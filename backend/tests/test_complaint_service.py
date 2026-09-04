"""
Tests: Complaint service — ticket creation, threaded messaging, status transitions, role-based admin access, and user isolation.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.complaint import Complaint, ComplaintCategory, ComplaintMessage, ComplaintPriority, ComplaintStatus
from app.models.user import User
from app.services import complaint_service as svc


def make_user(email="testuser@example.com", role="user"):
    return User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hashed_test_password",
        role=role,
        is_active=True,
    )


class TestComplaintServiceCRUD:
    @pytest.mark.asyncio
    async def test_create_complaint_success(self):
        user = make_user()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        complaint_id = uuid.uuid4()
        mock_complaint = Complaint(
            id=complaint_id,
            user_id=user.id,
            subject="Cannot connect Binance API",
            category=ComplaintCategory.EXCHANGE_CONNECTION.value,
            priority=ComplaintPriority.HIGH.value,
            status=ComplaintStatus.OPEN.value,
            description="API key returns 401 error repeatedly.",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            messages=[],
        )

        with patch.object(svc, "get_complaint", return_value=mock_complaint):
            res = await svc.create_complaint(
                db=mock_db,
                user=user,
                subject="Cannot connect Binance API",
                category=ComplaintCategory.EXCHANGE_CONNECTION.value,
                priority="high",
                description="API key returns 401 error repeatedly.",
            )

            assert res.id == complaint_id
            assert res.subject == "Cannot connect Binance API"
            assert res.priority == "high"
            assert mock_db.add.called
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_create_complaint_empty_subject_raises(self):
        user = make_user()
        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="Subject cannot be empty"):
            await svc.create_complaint(
                db=mock_db,
                user=user,
                subject="",
                category="General Inquiry",
                priority="medium",
                description="Some description",
            )

    @pytest.mark.asyncio
    async def test_create_complaint_empty_description_raises(self):
        user = make_user()
        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="Description cannot be empty"):
            await svc.create_complaint(
                db=mock_db,
                user=user,
                subject="Valid subject",
                category="General Inquiry",
                priority="medium",
                description="",
            )

    @pytest.mark.asyncio
    async def test_get_complaint_user_isolation(self):
        user = make_user(role="user")
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(svc.ComplaintNotFoundError):
            await svc.get_complaint(mock_db, user, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_add_complaint_message_user_reply(self):
        user = make_user(role="user")
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        complaint = Complaint(
            id=uuid.uuid4(),
            user_id=user.id,
            subject="Bug report",
            status=ComplaintStatus.RESOLVED.value,
            messages=[],
        )

        with patch.object(svc, "get_complaint", return_value=complaint):
            await svc.add_complaint_message(
                db=mock_db,
                user=user,
                complaint_id=complaint.id,
                message="The issue still happens after restart.",
            )
            # Reopens / sets to in_progress on user follow-up
            assert complaint.status == ComplaintStatus.IN_PROGRESS.value
            assert mock_db.add.called
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_add_complaint_message_admin_reply(self):
        admin = make_user(role="admin")
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        complaint = Complaint(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            subject="Billing issue",
            status=ComplaintStatus.OPEN.value,
            messages=[],
        )

        with patch.object(svc, "get_complaint", return_value=complaint):
            await svc.add_complaint_message(
                db=mock_db,
                user=admin,
                complaint_id=complaint.id,
                message="We are investigating your account logs.",
            )
            # Transitions from OPEN to IN_PROGRESS on admin reply
            assert complaint.status == ComplaintStatus.IN_PROGRESS.value
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_update_complaint_status_valid(self):
        user = make_user()
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        complaint = Complaint(
            id=uuid.uuid4(),
            user_id=user.id,
            subject="Issue",
            status=ComplaintStatus.OPEN.value,
        )

        with patch.object(svc, "get_complaint", return_value=complaint):
            await svc.update_complaint_status(
                db=mock_db,
                user=user,
                complaint_id=complaint.id,
                status="resolved",
                resolution_notes="Issue resolved by user after updating IP whitelist.",
            )
            assert complaint.status == "resolved"
            assert complaint.resolution_notes == "Issue resolved by user after updating IP whitelist."

    @pytest.mark.asyncio
    async def test_update_complaint_status_invalid_raises(self):
        user = make_user()
        mock_db = AsyncMock()

        complaint = Complaint(
            id=uuid.uuid4(),
            user_id=user.id,
            subject="Issue",
            status=ComplaintStatus.OPEN.value,
        )

        with patch.object(svc, "get_complaint", return_value=complaint):
            with pytest.raises(ValueError, match="Invalid status"):
                await svc.update_complaint_status(
                    db=mock_db,
                    user=user,
                    complaint_id=complaint.id,
                    status="non_existent_status",
                )
