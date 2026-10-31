from pydantic import BaseModel


class JobExtraction(BaseModel):
    is_job_posting: bool | None = None
    is_closed: bool = False
    application_available: bool | None = None
    experience_level: str | None = None
    preferred_skills: list[str] = []
    responsibilities: list[str] = []
    posted_at: str | None = None
    deadline: str | None = None
    application_url: str | None = None
    remote_eligibility: str | None = None
    title: str
    company: str | None = None
    location: str | None = None
    salary_range: str | None = None
    # one of: full_time | part_time | contract | internship | temporary
    employment_type: str | None = None
    # one of: remote | onsite | hybrid
    work_mode: str | None = None
    requirements: list[str]
    description_summary: str
    contact_email: str | None = None
