"""
LangGraph agent state definition.

AgentState travels through every graph node. It contains:
- messages: the LangChain message list (user + assistant + tool messages)
- user_id: authenticated user's UUID — passed to every tool for ownership enforcement
- db: AsyncSession reference — used by tools to query the database
- error: set by the graph when a fatal error occurs

SECURITY: user_id and db are NEVER included in the LLM message stream.
They are graph-internal state only — not serialized to or from the LLM.
"""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State passed between all LangGraph nodes."""

    # Full conversation message history including ToolMessages.
    # add_messages reducer appends new messages rather than replacing.
    messages: Annotated[list[BaseMessage], add_messages]

    # Authenticated user context — graph-internal, never sent to the LLM.
    user_id: str

    # Database session — graph-internal, used by tools for DB access.
    db: Any

    # Set when a terminal error occurs (Groq failure, max iterations, etc.)
    # Tools return safe user-facing strings; this tracks graph-level failures.
    error: str | None

    # Tracks number of tool call rounds to enforce max_iterations.
    iteration_count: int
