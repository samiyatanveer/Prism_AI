"""
LangGraph ReAct agent graph for PrismAI assistant.

Architecture:
  [agent_node] ← ChatGroq with bound tools
       ↓ tool_calls present?
  [tool_node]  ← executes tools with user_id + db in config
       ↑_______↓  (loop back to agent)
       ↓ no tool_calls or max_iterations reached
     [END]

Security guarantees:
  - user_id and db never appear in LLM messages
  - Groq API key never logged or raised in exceptions
  - Max 5 tool-call iterations; graceful message on limit reached
"""

from __future__ import annotations

import asyncio
import os
import re
import socket
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.ai.prompts import SYSTEM_PROMPT
from app.ai.state import AgentState
from app.ai.tools import ALL_TOOLS
from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_ITERATIONS = 5
_GRACEFUL_LIMIT_MSG = (
    "I've performed several lookups but couldn't produce a complete answer "
    "within the allowed steps. Please try rephrasing your question or asking "
    "about one specific thing at a time."
)

# Backoff durations before a single automatic retry.
_RETRY_BACKOFF_TRANSIENT = 2.0   # seconds — for timeout / connection errors
_RETRY_BACKOFF_RATE_LIMIT = 12.0  # seconds — for 429 rate-limit errors


_GROQ_KEY_PATTERN = re.compile(r"gsk_[A-Za-z0-9_-]+")
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)(bearer\s+)[^\s,;]+")
_API_KEY_QUERY_PATTERN = re.compile(r"(?i)(api[_-]?key=)[^\s,&]+")


def _safe_exception_details(exc: Exception) -> tuple[str, int | None, str]:
    """Return diagnostic-only exception details with credentials removed."""
    status_code = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    if status_code is None and response is not None:
        status_code = getattr(response, "status_code", None)
    if not isinstance(status_code, int):
        status_code = None

    message = str(exc).replace("\n", " ").replace("\r", " ")
    message = _GROQ_KEY_PATTERN.sub("[REDACTED]", message)
    message = _BEARER_TOKEN_PATTERN.sub(r"\1[REDACTED]", message)
    message = _API_KEY_QUERY_PATTERN.sub(r"\1[REDACTED]", message)
    return type(exc).__name__, status_code, message[:500]


def _safe_transport_details(exc: Exception) -> tuple[str, str]:
    """Classify and summarize the exception chain behind an SDK connection error."""
    chain: list[Exception] = []
    current: Exception | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(chain) < 5:
        chain.append(current)
        seen.add(id(current))
        cause = current.__cause__ or current.__context__
        current = cause if isinstance(cause, Exception) else None

    type_names = {type(item).__name__.lower() for item in chain}
    details = " ".join(str(item).lower() for item in chain)
    if any(isinstance(item, socket.gaierror) for item in chain) or any(
        marker in details
        for marker in ("getaddrinfo", "name or service not known", "temporary failure in name resolution")
    ):
        transport = "dns"
    elif "proxyerror" in type_names or "proxy" in details:
        transport = "proxy"
    elif any("ssl" in name for name in type_names) or any(
        marker in details for marker in ("tls", "certificate verify", "ssl")
    ):
        transport = "tls"
    elif any("timeout" in name for name in type_names) or "timed out" in details:
        transport = "timeout"
    elif any("connectionrefused" in name for name in type_names) or "connection refused" in details:
        transport = "connection_refused"
    elif any("connect" in name for name in type_names):
        transport = "connection"
    else:
        transport = "unknown"

    parts = []
    for item in chain:
        _, _, message = _safe_exception_details(item)
        parts.append(f"{type(item).__name__}: {message or '[no message]'}")
    return transport, " <- ".join(parts)


def _log_groq_failure(exc: Exception, *, attempt: int, retryable: bool) -> None:
    """Log a production-safe Groq/LangChain failure for diagnosis."""
    error_type, status_code, error_message = _safe_exception_details(exc)
    transport, cause_chain = _safe_transport_details(exc)
    https_proxy_set = bool(os.getenv("HTTPS_PROXY") or os.getenv("https_proxy"))
    http_proxy_set = bool(os.getenv("HTTP_PROXY") or os.getenv("http_proxy"))
    no_proxy_set = bool(os.getenv("NO_PROXY") or os.getenv("no_proxy"))
    logger.warning(
        f"Groq invocation failed: type={error_type}, status={status_code}, "
        f"error={error_message}, transport={transport}, causes={cause_chain}, "
        f"https_proxy_set={https_proxy_set}, http_proxy_set={http_proxy_set}, "
        f"no_proxy_set={no_proxy_set}, attempt={attempt}, retryable={retryable}"
    )


def _classify_groq_error(exc: Exception) -> tuple[bool, str, float]:
    """
    Classify a Groq / HTTP exception without leaking credential material.

    Returns (is_retryable, user_message, retry_delay_secs).
      - is_retryable: True when a single delayed retry is worth attempting.
      - user_message: A safe, specific string to surface if the error persists.
      - retry_delay_secs: How long to wait before the retry attempt.
    """
    name = type(exc).__name__
    msg = str(exc)

    # Groq SDK raises groq.RateLimitError (HTTP 429).
    # Retry once after a longer pause; the token bucket usually resets within 10 s.
    if "RateLimit" in name or "rate_limit" in msg.lower() or "429" in msg:
        return True, (
            "The AI service is rate-limited. Please wait a moment and try again."
        ), _RETRY_BACKOFF_RATE_LIMIT

    # HTTP 400: request payload too large (context overflow) or malformed tool call.
    # Not retryable — retrying the same payload will fail again.
    if "BadRequest" in name or "400" in msg:
        return False, (
            "Your request produced too much context for the AI to process in one go. "
            "Try asking about a specific asset or a smaller question."
        ), 0.0

    # groq.AuthenticationError (HTTP 401) — config problem, not transient.
    if "Authentication" in name or "401" in msg:
        return False, "AI assistant configuration error. Please contact support.", 0.0

    # groq.NotFoundError (HTTP 404) — model unavailable / removed.
    if "NotFound" in name or "404" in msg:
        return False, "The configured AI model is unavailable. Please contact support.", 0.0

    # groq.APITimeoutError / httpx.ReadTimeout / asyncio.TimeoutError — retryable.
    if (
        "Timeout" in name
        or "timeout" in msg.lower()
        or isinstance(exc, asyncio.TimeoutError)
    ):
        return True, (
            "The AI service did not respond in time. "
            "Please try again — your question has been noted."
        ), _RETRY_BACKOFF_TRANSIENT

    # groq.APIConnectionError / httpx network errors — retryable.
    if "Connection" in name or "connect" in msg.lower():
        return True, (
            "A network error occurred reaching the AI service. "
            "Please try again in a moment."
        ), _RETRY_BACKOFF_TRANSIENT

    # Fallback: unknown error, likely transient.
    return True, "The AI service is temporarily unavailable. Please try again in a moment.", _RETRY_BACKOFF_TRANSIENT


def _get_llm():
    """
    Instantiate ChatGroq. Called lazily so the app starts without GROQ_API_KEY.
    Raises RuntimeError (not ValueError) so the API layer can return 503.
    GROQ_API_KEY is never logged.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError(
            "AI assistant is not configured. "
            "Set the GROQ_API_KEY environment variable to enable it."
        )
    try:
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,   # passed directly; never logged
            timeout=settings.groq_timeout,
        )
        return llm.bind_tools(ALL_TOOLS)
    except Exception as exc:
        error_type, status_code, error_message = _safe_exception_details(exc)
        logger.warning(
            f"Groq model initialization failed: type={error_type}, "
            f"status={status_code}, error={error_message}"
        )
        # Do not re-raise the original exception — it may contain the API key
        raise RuntimeError("Failed to initialize AI model. Please try again later.") from None


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def agent_node(state: AgentState) -> dict:
    """
    Call the Groq LLM with the current message history.
    Injects the system prompt as the first message if not already present.
    Enforces max iteration limit.
    """
    # Check iteration limit before calling LLM
    iteration = state.get("iteration_count", 0)
    if iteration >= _MAX_ITERATIONS:
        return {
            "messages": [AIMessage(content=_GRACEFUL_LIMIT_MSG)],
            "error": "max_iterations_reached",
            "iteration_count": iteration,
        }

    messages = list(state["messages"])

    # Prepend system prompt if the conversation doesn't have one yet
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    try:
        llm = _get_llm()
        response = await llm.ainvoke(messages)
        return {
            "messages": [response],
            "error": None,
            "iteration_count": iteration + 1,
        }
    except RuntimeError as exc:
        # Config error (no API key) or model init failure — not retryable.
        error_msg = str(exc)
        logger.warning(
            f"Groq model unavailable before invocation: type={type(exc).__name__}, "
            f"error={error_msg}"
        )
        return {
            "messages": [AIMessage(content=error_msg)],
            "error": error_msg,
            "iteration_count": iteration,
        }
    except Exception as exc:
        # Classify the Groq / HTTP error without leaking the API key.
        is_retryable, error_msg, retry_delay = _classify_groq_error(exc)
        _log_groq_failure(exc, attempt=1, retryable=is_retryable)

        if is_retryable:
            # One automatic retry after an error-class-specific backoff.
            # Rate limits use a longer pause; transient errors use a short one.
            await asyncio.sleep(retry_delay)
            try:
                llm = _get_llm()
                response = await llm.ainvoke(messages)
                return {
                    "messages": [response],
                    "error": None,
                    "iteration_count": iteration + 1,
                }
            except Exception as retry_exc:
                _, error_msg, _ = _classify_groq_error(retry_exc)
                _log_groq_failure(retry_exc, attempt=2, retryable=False)

        return {
            "messages": [AIMessage(content=error_msg)],
            "error": error_msg,
            "iteration_count": iteration,
        }


def should_continue(state: AgentState) -> Literal["tools", END]:
    """
    Route decision: call tools or end the graph.
    Stop if: error set, max iterations, or last message has no tool calls.
    """
    if state.get("error"):
        return END

    messages = state["messages"]
    last_message = messages[-1] if messages else None

    if not isinstance(last_message, AIMessage):
        return END

    if not getattr(last_message, "tool_calls", None):
        return END

    if state.get("iteration_count", 0) >= _MAX_ITERATIONS:
        return END

    return "tools"


def build_graph() -> StateGraph:
    """
    Construct and compile the PrismAI LangGraph ReAct graph.

    The ToolNode executes tools with the user_id and db passed via config
    (RunnableConfig) — these values come from the graph invocation call,
    not from the LLM.
    """
    tool_node = ToolNode(ALL_TOOLS)

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)

    builder.set_entry_point("agent")
    builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")

    return builder.compile()


# Lazily compiled graph — compiled once on first use
_graph = None
_graph_lock = asyncio.Lock()


async def get_graph():
    """Return the compiled graph, compiling it on first call."""
    global _graph
    if _graph is None:
        async with _graph_lock:
            if _graph is None:
                _graph = build_graph()
    return _graph
