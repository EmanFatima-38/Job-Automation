from app.ai.client import parse_structured
from app.ai.prompts.match_scoring import MATCH_SCORING_SYSTEM_PROMPT
from app.ai.schemas.job_extraction_schema import JobExtraction
from app.ai.schemas.match_score_schema import MatchScore
from app.ai.schemas.resume_profile_schema import ResumeProfile
from app.config import get_settings

settings = get_settings()


def score_match(profile: ResumeProfile, job: JobExtraction) -> MatchScore:
    user_content = (
        f"RESUME PROFILE:\n{profile.model_dump_json(indent=2)}\n\n"
        f"JOB:\n{job.model_dump_json(indent=2)}"
    )
    result = parse_structured(
        model=settings.match_scoring_model,
        system=MATCH_SCORING_SYSTEM_PROMPT,
        user_content=user_content,
        output_model=MatchScore,
        # Feeding the full job posting (not just a short summary) gives the model more to
        # reason about, so it tends to produce longer matched/missing skill lists and
        # rationale - 1024 was tight enough to occasionally truncate mid-JSON and fail
        # schema validation.
        max_tokens=2048,
    )
    # Enforce missing-evidence handling even when the model omits structured concerns.
    from types import SimpleNamespace
    from app.services.recommendation_policy import mandatory_evidence
    _, concerns = mandatory_evidence(SimpleNamespace(requirements=job.requirements,
        raw_input_text=job.description_summary), profile.model_dump())
    result.eligibility_concerns = list(dict.fromkeys(result.eligibility_concerns + concerns))
    if result.eligibility_concerns and result.score > 69:
        result.score = 69
        result.rationale += ' Score capped because mandatory eligibility is unresolved.'
    names = [project.name for project in profile.projects if project.name]
    result.relevant_projects = [name for name in names if name in result.relevant_projects or name.lower() in result.rationale.lower()]
    if any('enrollment' in reason.lower() for reason in concerns):
        result.matched_skills = [skill for skill in result.matched_skills if not any(word in skill.lower() for word in ('enroll', 'student', 'studying'))]
    return result
