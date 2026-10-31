import uuid

from pydantic import BaseModel

from app.ai.schemas.resume_profile_schema import ResumeProfile


class ResumeRead(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_type: str
    is_primary: bool
    parse_status: str
    parse_error: str | None
    structured_profile: ResumeProfile | None

    model_config = {"from_attributes": True}


class ResumeUpdate(BaseModel):
    is_primary: bool | None = None
