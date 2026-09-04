from app.config import Settings, normalize_database_url


VALID_ENCRYPTION_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="


def test_normalize_railway_postgresql_url_for_asyncpg():
    url = "postgresql://postgres:secret@switchback.proxy.rlwy.net:5432/railway"

    assert normalize_database_url(url) == (
        "postgresql+asyncpg://postgres:secret@switchback.proxy.rlwy.net:5432/railway"
    )


def test_settings_normalizes_railway_url_before_engines_consume_it():
    settings = Settings(
        database_url="postgresql://postgres:secret@switchback.proxy.rlwy.net:5432/railway",
        secret_key="test-secret",
        encryption_key=VALID_ENCRYPTION_KEY,
    )

    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_normalize_legacy_postgres_url_for_asyncpg():
    assert normalize_database_url("postgres://user:pass@localhost:5432/prism_ai") == (
        "postgresql+asyncpg://user:pass@localhost:5432/prism_ai"
    )


def test_preserve_local_asyncpg_url():
    url = "postgresql+asyncpg://prism_user:test_pass@localhost:5432/prism_ai"

    assert normalize_database_url(url) == url


def test_replace_explicit_sync_postgres_driver():
    assert normalize_database_url("postgresql+psycopg2://user:pass@db:5432/prism_ai") == (
        "postgresql+asyncpg://user:pass@db:5432/prism_ai"
    )
