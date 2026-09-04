"""
PrismAI FastAPI application factory.

The lifespan context manager handles startup/shutdown concerns:
  - Configures structured logging
  - Warms up the database connection pool
  - Verifies Redis connectivity

CORS, request logging middleware, and all routers are registered here.
"""

from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import is_rate_limited
from app.database import AsyncSessionLocal, engine

settings = get_settings()
logger = get_logger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown procedures."""
    configure_logging(settings.log_level)
    logger.info(
        "Starting PrismAI backend",
        extra={
            "version": settings.app_version,
            "environment": settings.app_env,
        },
    )

    # Warm up database pool
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connection pool ready")
    except Exception as exc:
        logger.error("Database connection failed on startup", extra={"error": str(exc)})
        # Don't crash — health endpoint will report the degraded state

    # Verify Redis
    try:
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        logger.info("Redis connection verified")
    except Exception as exc:
        logger.warning(
            "Redis unavailable on startup — caching will be disabled",
            extra={"error": str(exc)},
        )

    yield  # ← application runs here

    # Shutdown
    await engine.dispose()
    logger.info("PrismAI backend shut down cleanly")


# ── Application factory ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-Powered Crypto Trading Intelligence Platform",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,  # Required for httpOnly cookie exchange
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def sensitive_endpoint_rate_limit(request: Request, call_next):
        """Limit auth, AI, and exchange traffic before credential work begins."""
        if is_rate_limited(request):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait before retrying."},
                headers={"Retry-After": "60"},
            )
        return await call_next(request)

    @app.middleware("http")
    async def security_response_headers(request: Request, call_next):
        """Add browser-safe defaults without exposing implementation details."""
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        # API responses can contain user-specific portfolio and support data.
        response.headers.setdefault("Cache-Control", "no-store")
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    # ── Routes ───────────────────────────────────────────────
    app.include_router(api_router)

    # ── Global exception handler ──────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            extra={"path": request.url.path, "method": request.method},
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )

    return app


app = create_app()
