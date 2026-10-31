import re

from app.ai.client import generate_text
from app.ai.prompts.content_generation import (
    COVER_LETTER_SYSTEM_PROMPT,
    FOLLOWUP_EMAIL_SYSTEM_PROMPT,
    RESUME_BULLETS_SYSTEM_PROMPT,
)
from app.ai.schemas.job_extraction_schema import JobExtraction
from app.ai.schemas.resume_profile_schema import ResumeProfile
from app.config import get_settings

settings = get_settings()

_HTML_BREAK = re.compile(r"<br\s*/?>|</p>|<p>", re.I)
_BULLET_PREFIX = re.compile(r"^[\s\-*•\d.)]+")
_SUBJECT_PREFIX = re.compile(r"^subject:\s*", re.I)


def _strip_html_breaks(text: str) -> str:
    """Some models default to HTML line breaks instead of real newlines even when told
    this is plain text - never trust the prompt alone, normalize defensively since this
    is rendered as plain text, not HTML."""
    return _HTML_BREAK.sub("\n", text)


def _context(profile: ResumeProfile, job: JobExtraction) -> str:
    return (
        f"RESUME PROFILE:\n{profile.model_dump_json(indent=2)}\n\n"
        f"JOB:\n{job.model_dump_json(indent=2)}"
    )


def generate_cover_letter(profile: ResumeProfile, job: JobExtraction) -> str:
    # Plain text, not structured JSON - strict json_schema mode reliably truncates long
    # free-text output on this model (cuts off after ~60 tokens with finish_reason="stop"
    # even with a generous max_tokens budget); the identical prompt without response_format
    # produces a complete, well-formed letter. See app/ai/client.py:generate_text.
    content = generate_text(
        model=settings.generation_model,
        system=COVER_LETTER_SYSTEM_PROMPT,
        user_content=_context(profile, job),
        max_tokens=2048,
    )
    return _strip_html_breaks(content).strip()


def generate_resume_bullets(profile: ResumeProfile, job: JobExtraction) -> list[str]:
    text = generate_text(
        model=settings.generation_model,
        system=RESUME_BULLETS_SYSTEM_PROMPT,
        user_content=_context(profile, job),
        max_tokens=2048,
    )
    bullets = []
    for line in text.splitlines():
        cleaned = _BULLET_PREFIX.sub("", _strip_html_breaks(line)).strip()
        if cleaned:
            bullets.append(cleaned)
    return bullets


def generate_followup_email(
    profile: ResumeProfile, job: JobExtraction, days_since_applied: int, attempt_number: int
) -> tuple[str, str]:
    """Returns (subject, body). Model is instructed to emit "Subject: ..." on the first
    line, a blank line, then the body - parsed defensively since free text, not structured
    output, is what this model reliably produces (see generate_cover_letter)."""
    text = generate_text(
        model=settings.generation_model,
        system=FOLLOWUP_EMAIL_SYSTEM_PROMPT,
        user_content=(
            f"{_context(profile, job)}\n\n"
            f"DAYS SINCE APPLYING: {days_since_applied}\n"
            f"FOLLOW-UP ATTEMPT NUMBER: {attempt_number}"
        ),
        max_tokens=1024,
    )
    lines = _strip_html_breaks(text).strip().splitlines()
    subject = _SUBJECT_PREFIX.sub("", lines[0]).strip() if lines else "Following up on my application"
    body = "\n".join(lines[1:]).strip()
    return subject, body
