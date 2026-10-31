import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.base import UUIDMixin


class OpportunityDelivery(Base, UUIDMixin):
    __tablename__ = 'opportunity_deliveries'
    __table_args__ = (UniqueConstraint('user_id', 'job_id', name='uq_opportunity_delivery'),)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
