"""
Complaint and Support Pydantic schemas for request validation and API responses.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ComplaintCategoryEnum(str, Enum):
    ACCOUNT_SECURITY = "Account & Security"
    EXCHANGE_CONNECTION = "Exchange Connection"
    MARKET_DATA = "Market & Charts Data"
    AI_ASSISTANT = "AI Assistant & Analyses"
    PORTFOLIO_TRACKING = "Portfolio Tracking"
    BUG_REPORT = "Bug Report"
    GENERAL_INQUIRY = "General Inquiry"


class ComplaintPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ComplaintStatusEnum(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ComplaintCreate(BaseModel):
    """Payload to submit a new complaint or support ticket."""

    subject: str = Field(
        ...,
        min_length=3,
        max_length=150,
        description="Brief subject line describing the issue",
        examples=["Cannot sync Binance exchange portfolio"],
    )
    category: ComplaintCategoryEnum = Field(
        default=ComplaintCategoryEnum.GENERAL_INQUIRY,
        description="Issue classification",
    )
    priority: ComplaintPriorityEnum = Field(
        default=ComplaintPriorityEnum.MEDIUM,
        description="User-perceived urgency",
    )
    description: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Detailed description of the issue or complaint",
    )


class ComplaintMessageCreate(BaseModel):
    """Payload to add a reply message to a complaint thread."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Message reply text",
    )


class ComplaintStatusUpdate(BaseModel):
    """Payload to update the status or resolution notes of a complaint."""

    status: ComplaintStatusEnum
    resolution_notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Staff or user resolution summary",
    )


class ComplaintMessageResponse(BaseModel):
    """Single message within a complaint conversation thread."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    complaint_id: uuid.UUID
    sender_id: uuid.UUID
    sender_role: str
    message: str
    created_at: datetime


class ComplaintResponse(BaseModel):
    """Summary item in a user's complaints list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    subject: str
    category: str
    priority: str
    status: str
    description: str
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ComplaintDetailResponse(BaseModel):
    """Full detail of a complaint including complete message thread."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    subject: str
    category: str
    priority: str
    status: str
    description: str
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[ComplaintMessageResponse] = []


class ComplaintSummaryResponse(BaseModel):
    """Counts of complaints by status for dashboards and portal overview."""

    total: int = 0
    open: int = 0
    in_progress: int = 0
    resolved: int = 0
    closed: int = 0
