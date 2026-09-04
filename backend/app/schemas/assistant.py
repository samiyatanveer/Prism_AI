"""Request and response schemas for the AI assistant endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """POST /assistant/chat — send a message to the AI assistant."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's natural-language question or message.",
    )
    session_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Existing session UUID to continue, or null to start a new session.",
    )


# ── Responses ─────────────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    """Response from POST /assistant/chat."""

    session_id: uuid.UUID
    message: str
    role: str = "assistant"
    created_at: datetime


class ChatMessageResponse(BaseModel):
    """A single message in a chat session."""

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ChatSessionSummary(BaseModel):
    """Summary row returned in GET /assistant/sessions list."""

    id: uuid.UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ChatSessionDetail(BaseModel):
    """Full session with all messages, returned by GET /assistant/sessions/{id}."""

    id: uuid.UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse]
