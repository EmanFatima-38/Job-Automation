from app.ai.client import parse_structured
from app.ai.prompts.resume_parsing import RESUME_PARSING_SYSTEM_PROMPT
from app.ai.schemas.resume_profile_schema import ResumeProfile
from app.config import get_settings

settings = get_settings()


def parse_resume(raw_text: str) -> ResumeProfile:
    return parse_structured(
        model=settings.resume_parsing_model,
        system=RESUME_PARSING_SYSTEM_PROMPT,
        user_content=raw_text,
        output_model=ResumeProfile,
        max_tokens=4096,
    )
