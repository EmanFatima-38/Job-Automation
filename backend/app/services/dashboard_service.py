import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.job import Job
from app.models.match import Match
from app.models.resume import Resume
from app.models.user import User
from app.services.discovery_backlog import match_context
from app.services.recommendation_policy import recommendation
from app.schemas.dashboard import DashboardJobRow, DashboardStats

ALL_STATUSES = ["saved", "applied", "interview", "offer", "rejected"]


def get_stats(db: Session, user_id: uuid.UUID) -> DashboardStats:
    rows = db.execute(
        select(Application.status, func.count())
        .where(Application.user_id == user_id)
        .group_by(Application.status)
    ).all()

    counts = {status_name: 0 for status_name in ALL_STATUSES}
    for status_value, count in rows:
        counts[status_value] = count

    return DashboardStats(total=sum(counts.values()), **counts)


def get_dashboard_jobs(db: Session, user_id: uuid.UUID) -> list[DashboardJobRow]:
    jobs = list(
        db.scalars(select(Job).where(Job.user_id == user_id).order_by(Job.created_at.desc()))
    )

    primary = db.scalar(select(Resume).where(Resume.user_id == user_id, Resume.is_primary.is_(True)))
    user = db.get(User, user_id)
    rows: list[DashboardJobRow] = []
    for job in jobs:
        match = db.scalar(
            select(Match).where(Match.job_id == job.id, Match.resume_id == primary.id).order_by(Match.scored_at.desc())
        ) if primary else None
        if match and match.context_hash and match.context_hash != match_context(user, primary, job):
            match = None
        application = db.scalar(
            select(Application).where(Application.job_id == job.id, Application.user_id == user_id)
        )
        rows.append(
            DashboardJobRow(
                job_id=job.id,
                research={**(job.research or {}), **recommendation(job, user, primary, match)},
                title=job.title,
                company=job.company,
                location=job.location,
                employment_type=job.employment_type,
                work_mode=job.work_mode,
                extraction_status=job.extraction_status,
                match_score=match.match_score if match else None,
                missing_skills=match.missing_skills if match else None,
                application_id=application.id if application else None,
                application_status=application.status if application else None,
            )
        )
    return rows
