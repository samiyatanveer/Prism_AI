"""
Alembic async migration environment.

- Loads DATABASE_URL from the application settings (never alembic.ini).
- Imports all models via app.models so autogenerate can detect schema changes.
- Uses run_migrations_online with asyncio for compatibility with asyncpg.
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ``alembic`` is installed as a console script, so Python's import path does
# not reliably contain the backend directory when the command is launched.
# Add it explicitly before importing application models/settings.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import models so autogenerate can detect all tables ──────────────────────
# This import is intentionally side-effect-only; linters may flag it unused.
import app.models  # noqa: F401, E402
from app.models.base import Base  # noqa: E402

target_metadata = Base.metadata

# ── Load the database URL from application settings ──────────────────────────
# Never read from alembic.ini — always from the environment.
from app.config import get_settings  # noqa: E402

_settings = get_settings()
# Settings normalizes Railway's postgres[ql]:// URL to the asyncpg URL used by
# both the app engine and this migration engine. Keep Alembic on that same
# driver so it never falls back to an unavailable synchronous psycopg driver.
config.set_main_option("sqlalchemy.url", _settings.database_url)


# ── Migration helpers ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection (useful for review)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
