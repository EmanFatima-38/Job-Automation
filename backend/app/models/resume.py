import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Resume(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf | docx

    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="resumes")
