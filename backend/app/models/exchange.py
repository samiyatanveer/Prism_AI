"""Connected exchange model — encrypted credential storage."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConnectedExchange(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A user's connected crypto exchange account.

    API key and secret are encrypted with AES-256-GCM before storage
    (see ``app.core.security.encrypt_credential``). They are decrypted
    only by the backend exchange integration layer — never returned to
    the frontend or included in any API response.

    v1 integration is read-only; the ``permissions`` field documents what
    permissions the user granted when connecting.
    """

    __tablename__ = "connected_exchanges"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exchange_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "binance"

    # Optional human-friendly label set by the user at connect time
    display_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # AES-256-GCM encrypted blobs — never query or return as-is
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_api_secret: Mapped[str] = mapped_column(Text, nullable=False)

    # Human-readable permission summary (e.g. "read-only spot")
    permissions: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="connected_exchanges")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<ConnectedExchange id={self.id} user_id={self.user_id}"
            f" exchange={self.exchange_name!r} active={self.is_active}>"
        )
