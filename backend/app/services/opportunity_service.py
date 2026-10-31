from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.database import SessionLocal
from app.models.user import User
from app.models.job import Job
from app.models.resume import Resume
from app.models.match import Match
from app.models.opportunity_delivery import OpportunityDelivery
from app.schemas.discovery import Preferences
from app.services.discovery_lock import discovery_lock
from app.services.email_account_service import get_email_account
from app.services.email_service import send_email
from app.services.job_quality import eligibility, parse_date
from app.services.discovery_backlog import match_context
from app.services.recommendation_policy import recommendation


def send_opportunities(db, user):
    prefs = Preferences.model_validate(user.preferences or {})
    if not prefs.notifications_enabled:
        return 0
    account = get_email_account(db, user.id)
    if account is None:
        return 0
    latest = db.scalar(select(OpportunityDelivery).where(OpportunityDelivery.user_id == user.id).order_by(OpportunityDelivery.created_at.desc()))
    if latest and latest.created_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc) - timedelta(hours=prefs.notification_hours):
        return 0
    resume = db.scalar(select(Resume).where(Resume.user_id == user.id, Resume.is_primary.is_(True), Resume.parse_status == 'parsed'))
    if not resume:
        return 0
    rows = db.execute(select(Job, Match).join(Match, Match.job_id == Job.id).where(Job.user_id == user.id,
        Match.resume_id == resume.id, Match.match_score >= prefs.notification_min_score).order_by(Match.match_score.desc())).all()
    chosen = []
    for job, match in rows:
        if recommendation(job, user, resume, match, use_plan=False)['recommendation_status'] != 'recommended':
            continue
        research = job.research or {}
        rejected, concerns = eligibility(job, prefs.model_dump())
        checked = parse_date(research.get('last_verified_at'))
        if rejected or concerns or research.get('state') != 'active' or not checked or checked < datetime.now(timezone.utc) - timedelta(days=1):
            continue
        if match.context_hash != match_context(user, resume, job):
            continue
        if db.scalar(select(OpportunityDelivery.id).where(OpportunityDelivery.user_id == user.id, OpportunityDelivery.job_id == job.id)):
            continue
        chosen.append((job, match))
        if len(chosen) >= 10:
            break
    if not chosen:
        return 0
    # Reserve before SMTP. An uncertain delivery is never automatically resent.
    deliveries = [OpportunityDelivery(user_id=user.id, job_id=j.id, status='sending') for j, _ in chosen]
    db.add_all(deliveries)
    db.commit()
    body = 'New opportunities matching your saved preferences. Scores estimate fit, not hiring probability.\n\n'
    for job, match in chosen:
        body += f'{job.title} — {job.company}\nEstimated fit: {match.match_score}/100\n{match.rationale}\n{research_link(job)}\n\n'
    try:
        send_email(account, user.email, f'ApplyPilot: {len(chosen)} new opportunities', body)
    except Exception as exc:
        for row in deliveries:
            row.status = 'uncertain'
            row.error = str(exc)[:500]
        db.commit()
        return 0
    for row in deliveries:
        row.status = 'sent'
    db.commit()
    return len(chosen)


def run_opportunity_notifications():
    with discovery_lock('opportunity-notifications') as acquired:
        if not acquired:
            return
        with SessionLocal() as db:
            ids = list(db.scalars(select(User.id)))
        for user_id in ids:
            with SessionLocal() as db:
                try:
                    send_opportunities(db, db.get(User, user_id))
                except Exception:
                    db.rollback()
                    import logging
                    logging.getLogger(__name__).exception('Opportunity delivery failed for %s', user_id)


def research_link(job):
    return (job.research or {}).get('application_url') or job.source_url
