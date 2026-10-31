import uuid

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    portfolio_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)

    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    search_keywords: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crawl_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    followup_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    followup_first_days: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    followup_interval_days: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    followup_max_count: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    resumes: Mapped[list["Resume"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    email_account: Mapped["EmailAccount | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
