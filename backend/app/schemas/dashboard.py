import uuid

from pydantic import BaseModel


class DashboardStats(BaseModel):
    saved: int
    applied: int
    interview: int
    offer: int
    rejected: int
    total: int


class DashboardJobRow(BaseModel):
    research: dict = {}
    job_id: uuid.UUID
    title: str | None
    company: str | None
    location: str | None
    employment_type: str | None
    work_mode: str | None
    extraction_status: str
    match_score: int | None
    missing_skills: list[str] | None
    application_id: uuid.UUID | None
    application_status: str | None
