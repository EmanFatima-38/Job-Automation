from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Preferences(BaseModel):
    roles: list[str] = Field(default_factory=list, max_length=12)
    skills: list[str] = Field(default_factory=list, max_length=50)
    employment_types: list[Literal['full_time', 'part_time', 'contract', 'internship', 'temporary']] = []
    seniority: list[str] = Field(default_factory=list, max_length=8)
    cities: list[str] = Field(default_factory=list, max_length=12)
    countries: list[str] = Field(default_factory=list, max_length=8)
    work_modes: list[str] = []
    remote: bool = False
    remote_country: str = ''
    excluded_companies: list[str] = Field(default_factory=list, max_length=30)
    excluded_keywords: list[str] = Field(default_factory=list, max_length=30)
    portfolio_urls: list[str] = Field(default_factory=list, max_length=5)
    github_url: str = Field(default='', max_length=2048)
    projects: list[dict] = Field(default_factory=list, max_length=30)
    max_age_days: int | None = Field(default=None, ge=1, le=365)
    search_depth: Literal['basic', 'advanced'] = 'basic'
    max_queries: int = Field(default=6, ge=1, le=12)
    results_per_source: int = Field(default=10, ge=1, le=30)
    notifications_enabled: bool = False
    notification_min_score: int = Field(default=75, ge=0, le=100)
    notification_hours: int = Field(default=24, ge=1, le=168)


class SearchRequest(BaseModel):
    intent: str = Field(default='', max_length=2000)
    force: bool = False


class SearchPlan(BaseModel):
    roles: list[str] = []
    skills: list[str] = []
    locations: list[str] = []
    employment_types: list[str] = []
    seniority: list[str] = []
    work_modes: list[str] = []
    remote: bool = False
    remote_country: str = ''
    max_age_days: int | None = None
    queries: list[str] = []
    planner: str = 'fallback'
    # Saved-preferences identity at planning time; see job_quality.current_plan.
    preferences_hash: str = ''


class PortfolioRead(BaseModel):
    url: str
    refreshed_at: datetime
    text: str
