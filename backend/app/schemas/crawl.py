import uuid
from datetime import datetime

from pydantic import BaseModel


class CrawlRunRead(BaseModel):
    intent: str = ""
    plan: dict = {}
    id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    status: str
    jobs_found: int
    jobs_created: int
    source_results: list[dict]
    error_message: str | None

    model_config = {"from_attributes": True}
