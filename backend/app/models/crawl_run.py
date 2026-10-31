import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class CrawlRun(Base, UUIDMixin):
    __tablename__ = "crawl_runs"

    intent: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    plan: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success | partial | failed
    jobs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_results: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
