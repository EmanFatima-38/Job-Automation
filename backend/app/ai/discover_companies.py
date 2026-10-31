from app.ai.client import parse_structured
from app.ai.prompts.company_discovery import (
    COMPANY_JOB_EXTRACTION_SYSTEM_PROMPT,
    COMPANY_NAME_EXTRACTION_SYSTEM_PROMPT,
    INDUSTRY_LABEL_SYSTEM_PROMPT,
)
from app.ai.schemas.company_discovery_schema import (
    CompanyJobPostingsResult,
    CompanyNames,
    IndustryLabel,
)
from app.config import get_settings

settings = get_settings()


def infer_industry(target_roles: list[str]) -> str:
    result = parse_structured(
        model=settings.job_extraction_model,
        system=INDUSTRY_LABEL_SYSTEM_PROMPT,
        user_content=", ".join(target_roles) or "Software Engineer",
        output_model=IndustryLabel,
        max_tokens=512,
    )
    return result.industry


def extract_company_names(search_results_text: str) -> list[str]:
    result = parse_structured(
        model=settings.job_extraction_model,
        system=COMPANY_NAME_EXTRACTION_SYSTEM_PROMPT,
        user_content=search_results_text,
        output_model=CompanyNames,
        # This model does hidden reasoning that counts against max_tokens before it emits
        # the actual JSON - with a long combined-search-results input, a tight budget here
        # gets fully consumed by reasoning, leaving nothing for the answer (empty response).
        max_tokens=4096,
    )
    return result.names


def extract_company_postings(page_text: str, links: list[dict]) -> CompanyJobPostingsResult:
    links_text = "\n".join(f"- {link['text']!r} -> {link['href']}" for link in links)
    user_content = f"PAGE TEXT:\n{page_text}\n\nLINKS ON PAGE:\n{links_text}"
    return parse_structured(
        model=settings.job_extraction_model,
        system=COMPANY_JOB_EXTRACTION_SYSTEM_PROMPT,
        user_content=user_content,
        output_model=CompanyJobPostingsResult,
        max_tokens=4096,
    )
