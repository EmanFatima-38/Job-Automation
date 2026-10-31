from pydantic import BaseModel


class IndustryLabel(BaseModel):
    industry: str


class CompanyNames(BaseModel):
    names: list[str]


class CompanyJobPosting(BaseModel):
    title: str
    url: str | None = None


class CompanyJobPostingsResult(BaseModel):
    postings: list[CompanyJobPosting]
