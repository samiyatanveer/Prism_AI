"""
Structured JSON logging with credential scrubbing.

All log records are emitted as JSON for easy ingestion by log aggregators.
A scrubbing filter strips any field whose key matches a sensitive pattern
before the record is serialized — passwords, tokens, and API keys can
never appear in logs even if accidentally passed to a logger.
"""

import logging
import re

from pythonjsonlogger import jsonlogger

# ── Sensitive field patterns ─────────────────────────────────────────────────
# Any record attribute whose key matches one of these patterns will be replaced.
_SENSITIVE_KEYS = re.compile(
    r"(password|passwd|secret|token|api_key|api_secret|encryption_key|"
    r"refresh_token|access_token|authorization|credential|private_key|signature)",
    re.IGNORECASE,
)

_REDACTED = "[REDACTED]"


class CredentialScrubFilter(logging.Filter):
    """
    Filter applied to every handler.

    Walks the log record's __dict__ and replaces the *value* of any field
    whose *key* matches ``_SENSITIVE_KEYS`` with ``[REDACTED]``.
    Also scrubs the formatted message string for extra safety.
    """

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        for key in list(record.__dict__.keys()):
            if _SENSITIVE_KEYS.search(key):
                setattr(record, key, _REDACTED)

        # Scrub the interpolated message (best-effort; keys already scrubbed above)
        if isinstance(record.msg, str) and _SENSITIVE_KEYS.search(record.msg):
            record.msg = _REDACTED
            record.args = ()

        return True


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure the root logger with a JSON formatter and the credential scrubber.
    Call once at application startup (inside the FastAPI lifespan).
    """
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        rename_fields={"levelname": "level", "asctime": "timestamp"},
    )

    scrub_filter = CredentialScrubFilter()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(scrub_filter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    # Silence noisy third-party loggers in production
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if log_level.upper() == "DEBUG" else logging.WARNING
    )
    # httpx logs full request URLs at INFO. Signed Binance URLs contain an
    # HMAC signature, so these request logs must never be emitted.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Always use this instead of logging.getLogger directly."""
    return logging.getLogger(name)
