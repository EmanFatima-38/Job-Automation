import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class DiscoveredCompany(Base, UUIDMixin):
    """A company found via web search for a user's industry + city, cached so discovery
    (AI + search API calls) doesn't re-run on every crawl - only the cheap scrape step
    (no search cost) runs each time, with discovery itself refreshed periodically."""

    __tablename__ = "discovered_companies"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    homepage_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
