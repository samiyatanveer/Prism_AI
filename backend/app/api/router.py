"""Central API router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.routes import admin, alerts, analyses, assistant, auth, complaints, exchanges, health, market, portfolio, profile, watchlists

api_router = APIRouter()

# Health (no prefix — accessible at /health)
api_router.include_router(health.router)

# Auth
api_router.include_router(auth.router)

# Assistant
api_router.include_router(assistant.router)
api_router.include_router(assistant.ai_router)

# Exchanges
api_router.include_router(exchanges.router)

# Portfolio
api_router.include_router(portfolio.router)

# Market data
api_router.include_router(market.router)

# Watchlists
api_router.include_router(watchlists.router)

# Alerts
api_router.include_router(alerts.router)

# Saved Analyses & Reports
api_router.include_router(analyses.router)

# Support & Complaints
api_router.include_router(complaints.router)

# Profile preferences and session security
api_router.include_router(profile.router)
api_router.include_router(admin.router)

# Future routers:
# api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
