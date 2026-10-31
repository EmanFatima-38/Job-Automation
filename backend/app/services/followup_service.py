import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.client import AIParseError, AIRefusalError
from app.ai.generate_content import generate_followup_email
from app.ai.schemas.resume_profile_schema import ResumeProfile
from app.database import SessionLocal
from app.models.application import Application
from app.models.followup import FollowUp
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.services.email_account_service import get_email_account
from app.services.email_service import EmailSendError, send_email
from app.services.job_mapping import job_to_extraction


def _resume_for_application(
    db: Session, user_id: uuid.UUID, application: Application
) -> Resume | None:
    if application.resume_id is not None:
        return db.get(Resume, application.resume_id)
    return db.scalar(
        select(Resume).where(
            Resume.user_id == user_id,
            Resume.is_primary.is_(True),
            Resume.parse_status == "parsed",
        )
    )


def _eligible_applications(db: Session, user: User) -> list[Application]:
    now = datetime.now(timezone.utc)
    candidates = db.scalars(
        select(Application)
        .join(Job, Application.job_id == Job.id)
        .where(
            Application.user_id == user.id,
            Application.status == "applied",
            Application.followup_opt_out.is_(False),
            Job.contact_email.isnot(None),
        )
    )

    due: list[Application] = []
    for application in candidates:
        sent = list(application.followups)
        if len(sent) >= user.followup_max_count:
            continue
        if not sent:
            anchor = application.applied_at
            threshold_days = user.followup_first_days
        else:
            anchor = sent[-1].sent_at
            threshold_days = user.followup_interval_days
        if anchor is None:
            continue
        if (now - anchor).days >= threshold_days:
            due.append(application)
    return due


def run_followups_for_user(db: Session, user: User) -> list[FollowUp]:
    account = get_email_account(db, user.id)
    if account is None:
        return []

    results: list[FollowUp] = []
    for application in _eligible_applications(db, user):
        job = db.get(Job, application.job_id)
        resume = _resume_for_application(db, user.id, application)
        if resume is None or resume.structured_profile is None:
            continue

        profile = ResumeProfile(**resume.structured_profile)
        job_extraction = job_to_extraction(job)
        days_since_applied = (
            (datetime.now(timezone.utc) - application.applied_at).days if application.applied_at else 0
        )
        attempt_number = len(application.followups) + 1

        subject = ""
        body = ""
        try:
            subject, body = generate_followup_email(
                profile, job_extraction, days_since_applied, attempt_number
            )
            send_email(account, job.contact_email, subject, body)
            followup = FollowUp(application_id=application.id, status="sent", subject=subject, content=body)
        except (AIRefusalError, AIParseError, EmailSendError) as e:
            followup = FollowUp(
                application_id=application.id,
                status="failed",
                subject=subject,
                content=body,
                error=str(e),
            )
        db.add(followup)
        results.append(followup)

    db.commit()
    return results


def _run_all_followups() -> None:
    """Entry point for the scheduler: send due follow-ups for every user who has opted in."""
    db = SessionLocal()
    try:
        users = list(db.scalars(select(User).where(User.followup_enabled.is_(True))))
        for user in users:
            run_followups_for_user(db, user)
    finally:
        db.close()


def run_all_followups() -> None:
    from app.services.discovery_lock import discovery_lock
    with discovery_lock('employer-followups') as acquired:
        if acquired:
            _run_all_followups()
