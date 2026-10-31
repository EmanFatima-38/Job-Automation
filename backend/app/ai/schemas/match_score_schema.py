from pydantic import BaseModel, Field


class MatchScore(BaseModel):
    relevant_projects: list[str] = []
    eligibility_concerns: list[str] = []
    score: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    rationale: str
