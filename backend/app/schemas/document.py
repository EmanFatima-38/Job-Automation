import uuid
from typing import Literal

from pydantic import BaseModel


class DocumentCreate(BaseModel):
    resume_id: uuid.UUID
    doc_type: Literal["cover_letter", "resume_bullets"]


class DocumentRead(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    doc_type: str
    content: str
    model_used: str

    model_config = {"from_attributes": True}
