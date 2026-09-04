"""
Tests: AI Assistant API routes and schemas.

Verifies:
- ChatRequest validation (empty message, message too long)
- Response schema structure
- Session listing and detail schemas
- Error status code mappings
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError

from app.api.routes import assistant as assistant_routes
from app.database import get_db
from app.dependencies import get_current_user
from app.main import create_app
from app.schemas.assistant import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionDetail,
    ChatSessionSummary,
)
from app.services.assistant_service import _extract_final_response


class TestAssistantSchemas:
    def test_valid_chat_request(self):
        req = ChatRequest(message="What is my portfolio?")
        assert req.message == "What is my portfolio?"
        assert req.session_id is None

        session_id = uuid.uuid4()
        req_with_session = ChatRequest(message="Tell me more", session_id=session_id)
        assert req_with_session.session_id == session_id

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_message_too_long_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="a" * 2001)

    def test_chat_response_schema(self):
        session_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        resp = ChatResponse(
            session_id=session_id,
            message="Your BTC balance is 1.5 BTC.",
            role="assistant",
            created_at=now,
        )
        assert resp.session_id == session_id
        assert resp.role == "assistant"
        assert "1.5 BTC" in resp.message

    def test_chat_session_summary_schema(self):
        session_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        summary = ChatSessionSummary(
            id=session_id,
            title="What is my balance?",
            created_at=now,
            updated_at=now,
            message_count=4,
        )
        assert summary.id == session_id
        assert summary.message_count == 4

    def test_chat_session_detail_schema(self):
        session_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        detail = ChatSessionDetail(
            id=session_id,
            title="Portfolio check",
            created_at=now,
            updated_at=now,
            messages=[
                ChatMessageResponse(
                    id=uuid.uuid4(),
                    role="user",
                    content="Hello",
                    created_at=now,
                ),
                ChatMessageResponse(
                    id=uuid.uuid4(),
                    role="assistant",
                    content="Hi! How can I assist you with your crypto portfolio today?",
                    created_at=now,
                ),
            ],
        )
        assert len(detail.messages) == 2
        assert detail.messages[0].role == "user"
        assert detail.messages[1].role == "assistant"


class TestAssistantServiceSecurity:
    """Verify that credentials and internal keys are never exposed."""

    def test_no_credential_fields_in_schemas(self):
        schemas = [ChatResponse, ChatMessageResponse, ChatSessionSummary, ChatSessionDetail]
        forbidden_fields = {"api_key", "api_secret", "encrypted_api_key", "encrypted_api_secret", "groq_api_key"}

        for schema in schemas:
            fields = set(schema.model_fields.keys())
            overlap = fields & forbidden_fields
            assert not overlap, f"Forbidden fields {overlap} found in {schema.__name__}"


class TestAssistantChatRoute:
    def test_successful_chat_returns_the_assistant_response_shape(self, monkeypatch):
        session_id = uuid.uuid4()
        created_at = datetime.now(timezone.utc)
        send_message = AsyncMock(
            return_value={
                "session_id": session_id,
                "message": "BTC is trading above your selected threshold.",
                "role": "assistant",
                "created_at": created_at,
            }
        )
        monkeypatch.setattr(assistant_routes.svc, "send_message", send_message)

        async def override_current_user():
            return SimpleNamespace(id=uuid.uuid4())

        async def override_get_db():
            yield SimpleNamespace()

        app = create_app()
        app.dependency_overrides[get_current_user] = override_current_user
        app.dependency_overrides[get_db] = override_get_db

        response = TestClient(app).post(
            "/assistant/chat",
            json={"message": "How is BTC doing?", "session_id": None},
        )

        assert response.status_code == 200
        assert response.json() == {
            "session_id": str(session_id),
            "message": "BTC is trading above your selected threshold.",
            "role": "assistant",
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
        }
        send_message.assert_awaited_once()

    def test_groq_failure_is_an_http_error_not_an_assistant_message(self, monkeypatch):
        monkeypatch.setattr(
            assistant_routes.svc,
            "send_message",
            AsyncMock(
                side_effect=assistant_routes.svc.AssistantServiceUnavailableError(
                    "A network error occurred reaching the AI service. Please try again in a moment."
                )
            ),
        )

        async def override_current_user():
            return SimpleNamespace(id=uuid.uuid4())

        async def override_get_db():
            yield SimpleNamespace()

        app = create_app()
        app.dependency_overrides[get_current_user] = override_current_user
        app.dependency_overrides[get_db] = override_get_db

        response = TestClient(app).post(
            "/assistant/chat",
            json={"message": "How is BTC doing?", "session_id": None},
        )

        assert response.status_code == 503
        assert response.json() == {
            "detail": "A network error occurred reaching the AI service. Please try again in a moment."
        }

    @pytest.mark.asyncio
    async def test_graph_success_is_extracted_as_the_assistant_message(self):
        response = await _extract_final_response(
            {
                "messages": [
                    HumanMessage(content="How is BTC doing?"),
                    AIMessage(content="BTC is trading above your selected threshold."),
                ]
            }
        )

        assert response == "BTC is trading above your selected threshold."
