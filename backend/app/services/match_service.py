import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.schemas.resume_profile_schema import ResumeProfile
from app.ai.score_match import score_match
from app.models.job import Job
from app.models.match import Match
from app.models.resume import Resume
from app.models.user import User
from app.services.portfolio_service import candidate_profile
from app.services.discovery_backlog import match_context
from app.services.job_quality import eligibility, current_plan
from app.services.job_mapping import job_to_extraction
from app.services.recommendation_policy import mandatory_evidence


class MatchInputNotReadyError(Exception):
    pass


class MatchNotFoundError(Exception):
    pass


def score_and_store(db: Session, job: Job, resume: Resume) -> Match:
    """Score one job against one resume and upsert the Match row. Caller commits."""
    user = db.get(User, job.user_id)
    profile = ResumeProfile(**candidate_profile(user, resume))
    job_extraction = job_to_extraction(job)

    result = score_match(profile, job_extraction)

    match = db.scalar(select(Match).where(Match.job_id == job.id, Match.resume_id == resume.id))
    if match is None:
        match = Match(job_id=job.id, resume_id=resume.id)
        db.add(match)

    match.match_score = result.score
    match.matched_skills = result.matched_skills
    match.missing_skills = result.missing_skills
    match.rationale = result.rationale
    rejected, concerns = eligibility(job, user.preferences or {}, current_plan(job, user), profile.model_dump())
    _, mandatory = mandatory_evidence(job, profile.model_dump())
    all_concerns = list(dict.fromkeys(result.eligibility_concerns + concerns + rejected + mandatory))
    cap = 40 if rejected else 69 if all_concerns else 100
    match.match_score = min(result.score, cap)
    if result.score > cap:
        match.rationale += ' Evidence gate capped this estimate: ' + '; '.join(all_concerns)
    project_names = [p.name for p in profile.projects if p.name]
    projects = [name for name in project_names if name in result.relevant_projects or name.lower() in result.rationale.lower()]
    match.context_hash = match_context(user, resume, job)
    match.details = {'relevant_projects': projects,
                     'eligibility_concerns': all_concerns,
                     'score_label': 'Estimated fit, not hiring probability'}
    return match


def compute_match(
    db: Session, user_id: uuid.UUID, job_id: uuid.UUID, resume_id: uuid.UUID
) -> Match:
    job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user_id))
    resume = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id))

    if job is None or resume is None:
        raise MatchInputNotReadyError("Job or resume not found")
    if job.extraction_status != "extracted":
        raise MatchInputNotReadyError("Job has not been successfully extracted yet")
    if resume.parse_status != "parsed":
        raise MatchInputNotReadyError("Resume has not been successfully parsed yet")

    match = score_and_store(db, job, resume)
    db.commit()
    db.refresh(match)
    return match


def get_match(db: Session, user_id: uuid.UUID, job_id: uuid.UUID, resume_id: uuid.UUID) -> Match:
    match = db.scalar(
        select(Match)
        .join(Job, Match.job_id == Job.id)
        .where(Match.job_id == job_id, Match.resume_id == resume_id, Job.user_id == user_id)
    )
    if match is None:
        raise MatchNotFoundError
    user = db.get(User, user_id)
    resume = db.get(Resume, resume_id)
    job = db.get(Job, job_id)
    if match.context_hash and match.context_hash != match_context(user, resume, job):
        raise MatchNotFoundError
    return match


def list_matches(db: Session, user_id: uuid.UUID) -> list[Match]:
    return list(
        db.scalars(select(Match).join(Job, Match.job_id == Job.id).where(Job.user_id == user_id))
    )
