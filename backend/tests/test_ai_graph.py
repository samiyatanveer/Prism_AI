"""
Tests: LangGraph agent graph, node execution, Groq handling, and iteration limits.

Verifies:
- Direct answers terminate immediately
- Tool calls route to tool node and loop back to agent
- Max 5-iteration limit returns graceful user-safe response
- Groq error / missing API key returns safe error message without key exposure
"""

import pytest
import socket
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.ai.graph import build_graph, should_continue, agent_node, _MAX_ITERATIONS, _GRACEFUL_LIMIT_MSG
from app.ai.state import AgentState


class TestAIGraph:
    def test_should_continue_on_tool_calls(self):
        msg_with_tool = AIMessage(
            content="",
            tool_calls=[{"name": "get_portfolio_summary", "args": {}, "id": "call_1"}],
        )
        state: AgentState = {
            "messages": [HumanMessage(content="What is my balance?"), msg_with_tool],
            "user_id": "test-user-id",
            "db": None,
            "error": None,
            "iteration_count": 1,
        }
        assert should_continue(state) == "tools"

    def test_should_continue_ends_on_no_tool_calls(self):
        msg_no_tool = AIMessage(content="You have 0.5 BTC.")
        state: AgentState = {
            "messages": [HumanMessage(content="What is my balance?"), msg_no_tool],
            "user_id": "test-user-id",
            "db": None,
            "error": None,
            "iteration_count": 1,
        }
        from langgraph.graph import END
        assert should_continue(state) == END

    def test_should_continue_ends_on_max_iterations(self):
        msg_with_tool = AIMessage(
            content="",
            tool_calls=[{"name": "get_portfolio_summary", "args": {}, "id": "call_1"}],
        )
        state: AgentState = {
            "messages": [HumanMessage(content="What is my balance?"), msg_with_tool],
            "user_id": "test-user-id",
            "db": None,
            "error": None,
            "iteration_count": _MAX_ITERATIONS,
        }
        from langgraph.graph import END
        assert should_continue(state) == END

    @pytest.mark.asyncio
    async def test_agent_node_hits_max_iterations(self):
        state: AgentState = {
            "messages": [HumanMessage(content="Loop query")],
            "user_id": "test-user-id",
            "db": None,
            "error": None,
            "iteration_count": _MAX_ITERATIONS,
        }
        res = await agent_node(state)
        assert res["error"] == "max_iterations_reached"
        assert res["messages"][0].content == _GRACEFUL_LIMIT_MSG

    @pytest.mark.asyncio
    async def test_agent_node_missing_api_key(self):
        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "user_id": "test-user-id",
            "db": None,
            "error": None,
            "iteration_count": 0,
        }
        with patch("app.ai.graph.get_settings") as mock_settings:
            mock_settings.return_value.groq_api_key = ""
            res = await agent_node(state)
            assert "AI assistant is not configured" in res["messages"][0].content
            assert res["error"] is not None

    @pytest.mark.asyncio
    async def test_agent_node_groq_api_error(self):
        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "user_id": "test-user-id",
            "db": None,
            "error": None,
            "iteration_count": 0,
        }
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("Groq internal server error"))

        with patch("app.ai.graph._get_llm", return_value=mock_llm):
            res = await agent_node(state)
            assert "temporarily unavailable" in res["messages"][0].content
            assert res["error"] is not None
            # Verify secret/internal error is not in the message content
            assert "Groq internal server error" not in res["messages"][0].content

    @pytest.mark.asyncio
    async def test_agent_node_logs_sanitized_groq_failure(self, mocker, monkeypatch):
        class RateLimitFailure(Exception):
            status_code = 429

        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
            "user_id": "test-user-id",
            "db": None,
            "error": None,
            "iteration_count": 0,
        }
        failure = RateLimitFailure("429 gsk_this-must-never-appear")
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[failure, failure])
        log_warning = mocker.patch("app.ai.graph.logger.warning")
        for variable in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "NO_PROXY", "no_proxy"):
            monkeypatch.delenv(variable, raising=False)

        with patch("app.ai.graph._get_llm", return_value=mock_llm), patch(
            "app.ai.graph.asyncio.sleep", new=AsyncMock()
        ):
            result = await agent_node(state)

        assert "rate-limited" in result["messages"][0].content
        groq_logs = [
            call
            for call in log_warning.call_args_list
            if call.args[0].startswith("Groq invocation failed:")
        ]
        assert len(groq_logs) == 2
        assert groq_logs[0].args[0] == (
            "Groq invocation failed: type=RateLimitFailure, status=429, "
            "error=429 [REDACTED], transport=unknown, "
            "causes=RateLimitFailure: 429 [REDACTED], "
            "https_proxy_set=False, http_proxy_set=False, no_proxy_set=False, "
            "attempt=1, retryable=True"
        )
        assert "gsk_this-must-never-appear" not in groq_logs[0].args[0]

    def test_transport_diagnostic_identifies_and_sanitizes_dns_cause(self):
        from app.ai.graph import _safe_transport_details

        outer = Exception("Connection error")
        outer.__cause__ = socket.gaierror(
            -3, "Temporary failure in name resolution for gsk_never-log-this"
        )

        transport, causes = _safe_transport_details(outer)

        assert transport == "dns"
        assert "gaierror" in causes
        assert "gsk_never-log-this" not in causes
        assert "[REDACTED]" in causes

    @pytest.mark.asyncio
    async def test_full_graph_invocation_direct_reply(self):
        """Test full graph compiled flow with mocked LLM returning a direct answer."""
        graph = build_graph()
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Bitcoin is currently bullish."))

        with patch("app.ai.graph._get_llm", return_value=mock_llm):
            config = {"configurable": {"user_id": "test-id", "db": None}}
            output = await graph.ainvoke(
                {
                    "messages": [HumanMessage(content="How is BTC?")],
                    "user_id": "test-id",
                    "db": None,
                    "error": None,
                    "iteration_count": 0,
                },
                config=config,
            )
            assert len(output["messages"]) >= 2
            last_msg = output["messages"][-1]
            assert isinstance(last_msg, AIMessage)
            assert last_msg.content == "Bitcoin is currently bullish."
