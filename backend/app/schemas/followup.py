import uuid
from datetime import datetime

from pydantic import BaseModel


class FollowUpRead(BaseModel):
    id: uuid.UUID
    sent_at: datetime
    status: str
    subject: str
    error: str | None

    model_config = {"from_attributes": True}
