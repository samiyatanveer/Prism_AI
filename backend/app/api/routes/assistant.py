"""AI Assistant API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.assistant import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionDetail,
    ChatSessionSummary,
)
from app.services import assistant_service as svc

router = APIRouter(prefix="/assistant", tags=["Assistant"])
ai_router = APIRouter(prefix="/ai", tags=["Assistant"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with the read-only AI Assistant",
)
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Process a natural language question via LangGraph + Groq.
    Operates strictly on the authenticated user's portfolio and market data.
    """
    try:
        result = await svc.send_message(
            db=db,
            user=current_user,
            message=body.message,
            session_id=body.session_id,
        )
    except svc.SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message. Please try again.",
        )

    return ChatResponse(
        session_id=result["session_id"],
        message=result["message"],
        role=result["role"],
        created_at=result["created_at"],
    )


@router.get(
    "/sessions",
    response_model=list[ChatSessionSummary],
    summary="List chat sessions",
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatSessionSummary]:
    """List all previous chat sessions for the authenticated user."""
    sessions = await svc.list_sessions(db, current_user)
    return [
        ChatSessionSummary(
            id=s["id"],
            title=s["title"],
            created_at=s["created_at"],
            updated_at=s["updated_at"],
            message_count=s["message_count"],
        )
        for s in sessions
    ]


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetail,
    summary="Get chat session details",
)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionDetail:
    """Retrieve full conversation history for a specific chat session."""
    try:
        session = await svc.get_session(db, current_user, session_id)
    except svc.SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    return ChatSessionDetail(
        id=session["id"],
        title=session["title"],
        created_at=session["created_at"],
        updated_at=session["updated_at"],
        messages=[
            ChatMessageResponse(
                id=m["id"],
                role=m["role"],
                content=m["content"],
                created_at=m["created_at"],
            )
            for m in session["messages"]
        ],
    )


# The original /assistant URLs remain supported.  These aliases implement
# the documented public contract without duplicating orchestration logic.
ai_router.add_api_route("/chat", chat, methods=["POST"], response_model=ChatResponse)
ai_router.add_api_route("/sessions", list_sessions, methods=["GET"], response_model=list[ChatSessionSummary])
ai_router.add_api_route("/sessions/{session_id}", get_session, methods=["GET"], response_model=ChatSessionDetail)
