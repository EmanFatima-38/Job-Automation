import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Job(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("user_id", "external_id", name="uq_job_user_external_id"),)

    research: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True, index=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    source_type: Mapped[str] = mapped_column(String(10), nullable=False)  # url | text | crawl
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_input_text: Mapped[str] = mapped_column(Text, nullable=False)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    extraction_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="jobs")
