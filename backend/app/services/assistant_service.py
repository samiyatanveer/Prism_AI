"""
Assistant service — orchestrates LangGraph + conversation persistence.

Responsibilities:
  1. Create or reuse a ChatSession
  2. Load last N messages from DB as conversation context
  3. Run the LangGraph graph with user_id + db in config (never in LLM messages)
  4. Extract the final AI response from the graph output
  5. Persist user message + assistant response to chat_messages
  6. Return structured response

Security:
  - user_id passed only through RunnableConfig, not in message content
  - No credentials or internal IDs stored in message content
  - Groq errors surface as user-safe strings (graph handles this)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.graph import get_graph
from app.core.logging import get_logger
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User

logger = get_logger(__name__)

# Maximum messages loaded as context for each conversation turn
_CONTEXT_WINDOW = 10


class SessionNotFoundError(Exception):
    """Requested session does not exist or belongs to a different user."""


async def _get_or_create_session(
    db: AsyncSession,
    user: User,
    session_id: uuid.UUID | None,
    first_message: str,
) -> ChatSession:
    """Return existing session for this user, or create a new one."""
    if session_id is not None:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user.id,
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise SessionNotFoundError(
                f"Session {session_id} not found or does not belong to you."
            )
        return session

    # Create new session — title from first 60 chars of user message
    title = first_message[:60].strip() or None
    session = ChatSession(user_id=user.id, title=title)
    db.add(session)
    await db.flush()  # get the generated ID
    return session


async def _load_history(db: AsyncSession, session_id: uuid.UUID) -> list:
    """Load the last _CONTEXT_WINDOW messages for a session as LangChain messages."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(_CONTEXT_WINDOW)
    )
    rows = list(reversed(result.scalars().all()))
    history = []
    for row in rows:
        if row.role == "user":
            history.append(HumanMessage(content=row.content))
        else:
            history.append(AIMessage(content=row.content))
    return history


async def _extract_final_response(state: dict) -> str:
    """
    Pull the last AIMessage from graph output.
    Falls back to a safe error string if the graph produced nothing usable.
    """
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return str(msg.content)
    return "I was unable to generate a response. Please try again."


async def send_message(
    db: AsyncSession,
    user: User,
    message: str,
    session_id: uuid.UUID | None,
) -> dict:
    """
    Send a user message through the LangGraph assistant and persist the exchange.

    Returns:
        dict with session_id, message (assistant reply), role, created_at
    """
    # 1. Resolve session
    session = await _get_or_create_session(db, user, session_id, message)

    # 2. Load prior context
    history = await _load_history(db, session.id)

    # 3. Append the new user message
    messages = history + [HumanMessage(content=message)]

    # 4. Run LangGraph
    graph = await get_graph()
    config = {
        "configurable": {
            "user_id": str(user.id),
            "db": db,
        }
    }
    try:
        final_state = await graph.ainvoke(
            {
                "messages": messages,
                "user_id": str(user.id),
                "db": db,
                "error": None,
                "iteration_count": 0,
            },
            config=config,
        )
    except Exception:
        logger.exception("Unexpected graph error for user_id=%s", user.id)
        final_state = {
            "messages": messages + [
                AIMessage(content="An unexpected error occurred. Please try again.")
            ]
        }

    # 5. Extract assistant reply
    assistant_reply = await _extract_final_response(final_state)

    # 6. Persist both messages
    now = datetime.now(timezone.utc)
    db.add(ChatMessage(session_id=session.id, role="user", content=message, created_at=now))
    db.add(
        ChatMessage(session_id=session.id, role="assistant", content=assistant_reply, created_at=now)
    )
    # Update session timestamp
    session.updated_at = now
    await db.commit()

    return {
        "session_id": session.id,
        "message": assistant_reply,
        "role": "assistant",
        "created_at": now,
    }


async def list_sessions(db: AsyncSession, user: User) -> list[dict]:
    """Return all chat sessions for a user, most recent first."""
    result = await db.execute(
        select(
            ChatSession,
            func.count(ChatMessage.id).label("message_count"),
        )
        .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
        .where(ChatSession.user_id == user.id)
        .group_by(ChatSession.id)
        .order_by(ChatSession.updated_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": row.ChatSession.id,
            "title": row.ChatSession.title,
            "created_at": row.ChatSession.created_at,
            "updated_at": row.ChatSession.updated_at,
            "message_count": row.message_count,
        }
        for row in rows
    ]


async def get_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> dict:
    """Return a session with its full message history."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise SessionNotFoundError(f"Session {session_id} not found.")
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in session.messages
        ],
    }
