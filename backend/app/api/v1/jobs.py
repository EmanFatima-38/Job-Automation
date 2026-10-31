import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.models.match import Match
from app.services.recommendation_policy import recommendation
from app.parsers.html_fetcher import JobFetchError
from app.schemas.job import JobCreate, JobRead
from app.services.job_service import (
    JobNotFoundError,
    delete_job,
    get_job,
    ingest_job,
    list_jobs,
    reextract_job,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    data: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    try:
        return ingest_job(db, current_user.id, data)
    except JobFetchError as e:
        raise HTTPException(status_code=422, detail=f"{e} Paste the job description text instead.")


@router.get("", response_model=list[JobRead])
def get_jobs(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[JobRead]:
    return list_jobs(db, current_user.id)


@router.get("/{job_id}", response_model=JobRead)
def get_job_by_id(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    try:
        job = get_job(db, current_user.id, job_id)
        resume = db.scalar(select(Resume).where(Resume.user_id == current_user.id, Resume.is_primary.is_(True)))
        match = db.scalar(select(Match).where(Match.job_id == job.id, Match.resume_id == resume.id)) if resume else None
        result = JobRead.model_validate(job)
        result.research = {**(job.research or {}), **recommendation(job, current_user, resume, match)}
        return result
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.post("/{job_id}/reextract", response_model=JobRead)
def reextract(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    try:
        return reextract_job(db, current_user.id, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        delete_job(db, current_user.id, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")
