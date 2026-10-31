import uuid
from typing import Literal

from pydantic import BaseModel, model_validator


class JobCreate(BaseModel):
    source_type: Literal["url", "text"]
    source_url: str | None = None
    raw_text: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "JobCreate":
        if self.source_type == "text" and not self.raw_text:
            raise ValueError("raw_text is required when source_type is 'text'")
        if self.source_type == "url" and not self.source_url:
            raise ValueError("source_url is required when source_type is 'url'")
        return self


class JobRead(BaseModel):
    research: dict = {}
    canonical_url: str | None = None
    id: uuid.UUID
    source_type: str
    source_url: str | None
    raw_input_text: str
    title: str | None
    company: str | None
    location: str | None
    salary_range: str | None
    employment_type: str | None
    work_mode: str | None
    description_text: str | None
    requirements: list[str] | None
    contact_email: str | None
    extraction_status: str
    extraction_error: str | None

    model_config = {"from_attributes": True}
