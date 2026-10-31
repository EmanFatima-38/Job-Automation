import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class Match(Base, UUIDMixin):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("job_id", "resume_id", name="uq_match_job_resume"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    context_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)

    match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    missing_skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
