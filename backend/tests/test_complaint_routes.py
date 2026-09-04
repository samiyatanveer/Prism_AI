"""
Tests: Complaint API schemas, validation, security invariants, and route models.
"""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.complaint import (
    ComplaintCategoryEnum,
    ComplaintCreate,
    ComplaintDetailResponse,
    ComplaintMessageCreate,
    ComplaintMessageResponse,
    ComplaintPriorityEnum,
    ComplaintResponse,
    ComplaintStatusEnum,
    ComplaintStatusUpdate,
    ComplaintSummaryResponse,
)


class TestComplaintSchemas:
    def test_valid_complaint_create(self):
        req = ComplaintCreate(
            subject="Exchange sync timeout",
            category=ComplaintCategoryEnum.EXCHANGE_CONNECTION,
            priority=ComplaintPriorityEnum.HIGH,
            description="The sync operation times out after 30 seconds.",
        )
        assert req.subject == "Exchange sync timeout"
        assert req.category == ComplaintCategoryEnum.EXCHANGE_CONNECTION
        assert req.priority == ComplaintPriorityEnum.HIGH

    def test_complaint_create_short_subject_raises(self):
        with pytest.raises(ValidationError):
            ComplaintCreate(
                subject="Hi",  # min_length=3
                category=ComplaintCategoryEnum.GENERAL_INQUIRY,
                priority=ComplaintPriorityEnum.LOW,
                description="Valid description here",
            )

    def test_complaint_create_short_description_raises(self):
        with pytest.raises(ValidationError):
            ComplaintCreate(
                subject="Valid subject",
                category=ComplaintCategoryEnum.GENERAL_INQUIRY,
                priority=ComplaintPriorityEnum.LOW,
                description="Bad",  # min_length=5
            )

    def test_complaint_message_create_valid(self):
        req = ComplaintMessageCreate(message="Here is the screenshot.")
        assert req.message == "Here is the screenshot."

    def test_complaint_message_create_empty_raises(self):
        with pytest.raises(ValidationError):
            ComplaintMessageCreate(message="")

    def test_complaint_detail_response_serialization(self):
        now = datetime.now(timezone.utc)
        complaint_id = uuid.uuid4()
        user_id = uuid.uuid4()

        msg = ComplaintMessageResponse(
            id=uuid.uuid4(),
            complaint_id=complaint_id,
            sender_id=user_id,
            sender_role="user",
            message="Initial ticket description",
            created_at=now,
        )

        resp = ComplaintDetailResponse(
            id=complaint_id,
            user_id=user_id,
            subject="Portfolio glitch",
            category="Portfolio Tracking",
            priority="medium",
            status="open",
            description="Initial ticket description",
            resolution_notes=None,
            created_at=now,
            updated_at=now,
            messages=[msg],
        )

        assert resp.id == complaint_id
        assert len(resp.messages) == 1
        assert resp.messages[0].sender_role == "user"

    def test_complaint_summary_response(self):
        summary = ComplaintSummaryResponse(
            total=8,
            open=3,
            in_progress=2,
            resolved=2,
            closed=1,
        )
        assert summary.total == 8
        assert summary.open == 3
        assert summary.in_progress == 2


class TestComplaintSchemaSecurity:
    def test_no_sensitive_credentials_in_complaint_schemas(self):
        schemas = [
            ComplaintCreate,
            ComplaintMessageCreate,
            ComplaintStatusUpdate,
            ComplaintMessageResponse,
            ComplaintResponse,
            ComplaintDetailResponse,
            ComplaintSummaryResponse,
        ]
        forbidden_fields = {"api_key", "api_secret", "encrypted_api_key", "encrypted_api_secret", "password", "hashed_password"}

        for schema in schemas:
            fields = set(schema.model_fields.keys())
            overlap = fields & forbidden_fields
            assert not overlap, f"Forbidden fields {overlap} found in {schema.__name__}"
