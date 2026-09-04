"""Health check route — reports application and dependency status."""

import time

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.schemas.health import ComponentHealth, HealthResponse

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
    description=(
        "Returns the operational status of the application and its dependencies. "
        "No sensitive information (connection strings, credentials, internal paths) "
        "is ever included in the response."
    ),
)
async def health_check() -> HealthResponse:
    components: dict[str, ComponentHealth] = {}
    db_ok = True

    # ── Database ─────────────────────────────────────────────
    # Database availability determines the top-level application status.
    # A database failure means the application cannot serve authenticated requests.
    try:
        t0 = time.monotonic()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_latency = round((time.monotonic() - t0) * 1000, 2)
        components["database"] = ComponentHealth(status="ok", latency_ms=db_latency)
    except Exception:  # noqa: BLE001
        db_ok = False
        components["database"] = ComponentHealth(
            status="error",
            detail="Database unreachable.",  # no connection string exposed
        )

    # ── Redis ────────────────────────────────────────────────
    # Redis is an optional caching layer. No currently implemented feature
    # requires Redis — it is checked here for observability only.
    # A Redis outage does NOT affect the top-level application status.
    try:
        import redis.asyncio as aioredis

        t0 = time.monotonic()
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        redis_latency = round((time.monotonic() - t0) * 1000, 2)
        components["redis"] = ComponentHealth(status="ok", latency_ms=redis_latency)
    except Exception:  # noqa: BLE001
        # Redis unavailable — reported as a component detail only.
        # Top-level status is unaffected until a feature that requires
        # Redis is implemented and promoted to a required dependency.
        components["redis"] = ComponentHealth(
            status="unavailable",
            detail="Redis unreachable. Caching disabled.",
        )

    return HealthResponse(
        status="ok" if db_ok else "error",
        version=settings.app_version,
        environment=settings.app_env,
        components=components,
    )
