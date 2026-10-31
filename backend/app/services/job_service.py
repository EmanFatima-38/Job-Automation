import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.client import AIParseError, AIRefusalError
from app.ai.extract_job import extract_job
from app.models.job import Job
from app.models.resume import Resume
from app.parsers.html_fetcher import JobFetchError, fetch_job_posting_text
from app.schemas.job import JobCreate
from app.services.job_mapping import clean_optional_text
from app.services.job_quality import enrich_job, canonical_url
from app.services.match_service import score_and_store


class JobNotFoundError(Exception):
    pass


# Some crawl sources only return a short excerpt or just the title in their list API
# (not the full posting body). Below this length, treat the stored text as a stub and
# try fetching the real page once, the same way a manually pasted URL is fetched - so
# the job detail page always shows the complete posting instead of sending the user
# back to the source site to read it.
MIN_POSTING_LENGTH = 350


def _backfill_full_posting(db: Session, job: Job) -> None:
    if job.source_type != "crawl" or not job.source_url:
        return
    if len(job.raw_input_text or "") >= MIN_POSTING_LENGTH:
        return
    try:
        full_text = fetch_job_posting_text(job.source_url)
    except JobFetchError:
        return
    if len(full_text) > len(job.raw_input_text or ""):
        job.raw_input_text = full_text
        db.commit()
        db.refresh(job)


def _run_extraction(db: Session, job: Job) -> Job:
    job.extraction_status = "extracting"
    db.commit()

    enrich_job(job)

    db.commit()
    db.refresh(job)

    if job.extraction_status == "extracted":
        _try_auto_match(db, job)

    return job


def _try_auto_match(db: Session, job: Job) -> None:
    """Best-effort: score against the user's primary resume if one is parsed. Never raises."""
    resume = db.scalar(
        select(Resume).where(
            Resume.user_id == job.user_id,
            Resume.is_primary.is_(True),
            Resume.parse_status == "parsed",
        )
    )
    if resume is None:
        return
    try:
        score_and_store(db, job, resume)
        db.commit()
    except (AIRefusalError, AIParseError):
        db.rollback()


def ingest_job(db: Session, user_id: uuid.UUID, data: JobCreate) -> Job:
    if data.source_type == "url":
        raw_input_text = fetch_job_posting_text(data.source_url)  # type: ignore[arg-type]
    else:
        raw_input_text = data.raw_text

    canonical = canonical_url(data.source_url)
    if canonical:
        existing = db.scalar(select(Job).where(Job.user_id == user_id, Job.canonical_url == canonical))
        if existing is not None:
            return existing
    job = Job(
        canonical_url=canonical,
        user_id=user_id,
        source_type=data.source_type,
        source_url=data.source_url,
        raw_input_text=raw_input_text,
        extraction_status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return _run_extraction(db, job)


def get_job(db: Session, user_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user_id))
    if job is None:
        raise JobNotFoundError
    _backfill_full_posting(db, job)
    return job


def list_jobs(db: Session, user_id: uuid.UUID) -> list[Job]:
    return list(db.scalars(select(Job).where(Job.user_id == user_id)))


def reextract_job(db: Session, user_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    job = get_job(db, user_id, job_id)
    return _run_extraction(db, job)


def delete_job(db: Session, user_id: uuid.UUID, job_id: uuid.UUID) -> None:
    job = get_job(db, user_id, job_id)
    db.delete(job)
    db.commit()
