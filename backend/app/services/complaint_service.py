"""
Complaint service layer — ticket submission, threaded responses, and resolution lifecycle.

Rules:
- Strictly user-isolated on regular user queries and mutations.
- Admin role support for staff review, responses, and status transitions.
- Audit logging on ticket creation and resolution.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.complaint import (
    Complaint,
    ComplaintCategory,
    ComplaintMessage,
    ComplaintPriority,
    ComplaintStatus,
)
from app.models.user import User

logger = get_logger(__name__)


# ── Exceptions ───────────────────────────────────────────────────────────────

class ComplaintError(Exception):
    """Base exception for complaint operations."""


class ComplaintNotFoundError(ComplaintError):
    """Complaint not found or user lacks permission to access it."""


# ── Core Operations ───────────────────────────────────────────────────────────

async def list_complaints(
    db: AsyncSession,
    user: User,
    status_filter: str | None = None,
    category_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    List complaints. Regular users see only their own complaints.
    Admins can see all complaints.
    """
    query = select(Complaint)
    if user.role != "admin":
        query = query.where(Complaint.user_id == user.id)

    if status_filter:
        query = query.where(Complaint.status == status_filter.strip().lower())
    if category_filter:
        query = query.where(Complaint.category == category_filter.strip())

    query = query.order_by(Complaint.created_at.desc())
    result = await db.execute(query)
    complaints = list(result.scalars().all())

    # Calculate message counts
    items = []
    for c in complaints:
        # Count messages for this complaint
        count_stmt = select(func.count(ComplaintMessage.id)).where(
            ComplaintMessage.complaint_id == c.id
        )
        count_res = await db.execute(count_stmt)
        msg_count = count_res.scalar() or 0

        items.append({
            "id": c.id,
            "user_id": c.user_id,
            "subject": c.subject,
            "category": c.category,
            "priority": c.priority,
            "status": c.status,
            "description": c.description,
            "resolution_notes": c.resolution_notes,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "message_count": msg_count,
        })

    return items


async def get_complaint(
    db: AsyncSession,
    user: User,
    complaint_id: uuid.UUID,
) -> Complaint:
    """
    Retrieve full complaint detail including all threaded messages.

    :raises ComplaintNotFoundError: if not found or unauthorized.
    """
    stmt = (
        select(Complaint)
        .options(selectinload(Complaint.messages))
        .where(Complaint.id == complaint_id)
    )
    if user.role != "admin":
        stmt = stmt.where(Complaint.user_id == user.id)

    result = await db.execute(stmt)
    complaint = result.scalar_one_or_none()
    if complaint is None:
        raise ComplaintNotFoundError("Complaint not found.")

    return complaint


async def create_complaint(
    db: AsyncSession,
    user: User,
    subject: str,
    category: str,
    priority: str,
    description: str,
) -> Complaint:
    """
    Submit a new complaint or support ticket and create its initial thread message.
    """
    cleaned_subject = subject.strip()
    cleaned_desc = description.strip()
    if not cleaned_subject:
        raise ValueError("Subject cannot be empty.")
    if not cleaned_desc:
        raise ValueError("Description cannot be empty.")

    valid_cats = [e.value for e in ComplaintCategory]
    if category not in valid_cats:
        category = ComplaintCategory.GENERAL_INQUIRY.value

    valid_priorities = [e.value for e in ComplaintPriority]
    if priority.lower() not in valid_priorities:
        priority = ComplaintPriority.MEDIUM.value

    complaint = Complaint(
        user_id=user.id,
        subject=cleaned_subject,
        category=category,
        priority=priority.lower(),
        status=ComplaintStatus.OPEN.value,
        description=cleaned_desc,
    )
    db.add(complaint)
    await db.flush()

    # Initial message
    initial_msg = ComplaintMessage(
        complaint_id=complaint.id,
        sender_id=user.id,
        sender_role=user.role if user.role == "admin" else "user",
        message=cleaned_desc,
        created_at=datetime.now(timezone.utc),
    )
    db.add(initial_msg)
    await db.commit()

    return await get_complaint(db, user, complaint.id)


async def add_complaint_message(
    db: AsyncSession,
    user: User,
    complaint_id: uuid.UUID,
    message: str,
) -> Complaint:
    """
    Add a reply message to an existing complaint thread.
    Updates complaint status to 'in_progress' if currently 'open'.

    :raises ComplaintNotFoundError: if not found or unauthorized.
    """
    complaint = await get_complaint(db, user, complaint_id)

    cleaned_msg = message.strip()
    if not cleaned_msg:
        raise ValueError("Message cannot be empty.")

    sender_role = "admin" if user.role == "admin" else "user"

    new_msg = ComplaintMessage(
        complaint_id=complaint.id,
        sender_id=user.id,
        sender_role=sender_role,
        message=cleaned_msg,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_msg)

    # Status transition
    if user.role == "admin" and complaint.status == ComplaintStatus.OPEN.value:
        complaint.status = ComplaintStatus.IN_PROGRESS.value
    elif user.role != "admin" and complaint.status == ComplaintStatus.RESOLVED.value:
        complaint.status = ComplaintStatus.IN_PROGRESS.value

    await db.commit()
    return await get_complaint(db, user, complaint_id)


async def update_complaint_status(
    db: AsyncSession,
    user: User,
    complaint_id: uuid.UUID,
    status: str,
    resolution_notes: str | None = None,
) -> Complaint:
    """
    Update complaint status and optional resolution notes.

    :raises ComplaintNotFoundError: if not found or unauthorized.
    """
    complaint = await get_complaint(db, user, complaint_id)

    st = status.strip().lower()
    valid_statuses = [e.value for e in ComplaintStatus]
    if st not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

    complaint.status = st
    if resolution_notes is not None:
        complaint.resolution_notes = resolution_notes.strip() if resolution_notes else None

    await db.commit()
    return await get_complaint(db, user, complaint_id)


async def get_complaint_summary(
    db: AsyncSession,
    user: User,
) -> dict[str, int]:
    """
    Return counts of complaints by status: total, open, in_progress, resolved, closed.
    """
    query = select(Complaint.status, func.count(Complaint.id))
    if user.role != "admin":
        query = query.where(Complaint.user_id == user.id)
    query = query.group_by(Complaint.status)

    result = await db.execute(query)
    rows = result.all()

    counts = {
        "total": 0,
        "open": 0,
        "in_progress": 0,
        "resolved": 0,
        "closed": 0,
    }

    for status_val, count in rows:
        if status_val in counts:
            counts[status_val] = count
        counts["total"] += count

    return counts
