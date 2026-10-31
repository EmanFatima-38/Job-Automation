import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

StatusLiteral = Literal["saved", "applied", "interview", "offer", "rejected"]


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    resume_id: uuid.UUID | None = None


class ApplicationUpdate(BaseModel):
    status: StatusLiteral | None = None
    notes: str | None = None
    followup_opt_out: bool | None = None


class ApplicationRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID | None
    status: str
    applied_at: datetime | None
    notes: str | None
    followup_opt_out: bool
    followup_count: int = 0
    last_followup_at: datetime | None = None
    next_followup_due_at: datetime | None = None

    model_config = {"from_attributes": True}
