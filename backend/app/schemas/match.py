import uuid

from pydantic import BaseModel


class MatchRead(BaseModel):
    details: dict = {}
    id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    rationale: str | None

    model_config = {"from_attributes": True}
