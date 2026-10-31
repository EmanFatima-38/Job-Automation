from app.ai.client import parse_structured
from app.ai.prompts.job_extraction import JOB_EXTRACTION_SYSTEM_PROMPT
from app.ai.schemas.job_extraction_schema import JobExtraction
from app.config import get_settings

settings = get_settings()


def extract_job(raw_text: str) -> JobExtraction:
    return parse_structured(
        model=settings.job_extraction_model,
        system=JOB_EXTRACTION_SYSTEM_PROMPT,
        user_content=raw_text,
        output_model=JobExtraction,
        max_tokens=4096,
    )
