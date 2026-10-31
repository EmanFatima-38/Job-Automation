from pydantic import BaseModel


class CoverLetterOutput(BaseModel):
    content: str


class ResumeBulletsOutput(BaseModel):
    bullets: list[str]
