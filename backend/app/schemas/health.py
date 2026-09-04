"""Health check response schema."""

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    status: str  # "ok" | "degraded" | "error"
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    """
    Health endpoint response.

    Never includes connection strings, secrets, or internal paths.
    """

    status: str  # "ok" | "degraded" | "error"
    version: str
    environment: str
    components: dict[str, ComponentHealth]
