from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app import main
from app.config import Settings


VERCEL_ORIGIN = "https://prismai-roan.vercel.app"


def test_cors_origins_reads_railway_csv(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS", f"{VERCEL_ORIGIN}, http://localhost:3000, http://localhost:3001"
    )

    settings = Settings()

    assert settings.allowed_origins == [
        VERCEL_ORIGIN,
        "http://localhost:3000",
        "http://localhost:3001",
    ]


def test_cors_origins_keeps_legacy_allowed_origins_json(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.setenv("ALLOWED_ORIGINS", f'["{VERCEL_ORIGIN}", "http://localhost:3000"]')

    assert Settings().allowed_origins == [VERCEL_ORIGIN, "http://localhost:3000"]


def test_cors_origins_accepts_json_array(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS", f'["{VERCEL_ORIGIN}", "http://localhost:3000"]'
    )

    assert Settings().allowed_origins == [VERCEL_ORIGIN, "http://localhost:3000"]


def test_real_app_allows_vercel_preflight_with_credentials(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", f"{VERCEL_ORIGIN},http://localhost:3000")
    monkeypatch.setattr(main, "settings", Settings())

    client = TestClient(main.create_app())
    preflight = client.options(
        "/auth/register",
        headers={
            "Origin": VERCEL_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == VERCEL_ORIGIN
    assert preflight.headers["access-control-allow-credentials"] == "true"
    assert "content-type" in preflight.headers["access-control-allow-headers"]


def test_configured_origins_support_credentialed_normal_requests(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", f"{VERCEL_ORIGIN},http://localhost:3000")
    settings = Settings()
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/auth/refresh")
    def refresh():
        return {"ok": True}

    client = TestClient(app)
    response = client.post("/auth/refresh", headers={"Origin": VERCEL_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == VERCEL_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"

    disallowed = client.post("/auth/refresh", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in disallowed.headers
