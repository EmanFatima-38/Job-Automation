from pydantic import BaseModel


class ExperienceItem(BaseModel):
    title: str
    company: str
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = []


class EducationItem(BaseModel):
    degree: str
    school: str
    year: str | None = None


class Project(BaseModel):
    name: str = ''
    description: str = ''
    technologies: list[str] = []


class CandidatePreferences(BaseModel):
    roles: list[str] = []
    employment_types: list[str] = []
    seniority: list[str] = []
    cities: list[str] = []
    countries: list[str] = []
    work_modes: list[str] = []
    remote_country: str = ''
    excluded_companies: list[str] = []
    excluded_keywords: list[str] = []
    max_age_days: int | None = None


class ResumeProfile(BaseModel):
    projects: list[Project] = []
    portfolio_urls: list[str] = []
    github_url: str | None = None
    preferences: CandidatePreferences = CandidatePreferences()
    portfolio_evidence: list[str] = []
    summary: str
    skills: list[str]
    experience: list[ExperienceItem]
    education: list[EducationItem]
    city: str | None = None
    country: str | None = None
    target_roles: list[str] = []
