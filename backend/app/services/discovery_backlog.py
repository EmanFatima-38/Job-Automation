import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job
from app.models.match import Match
from app.services.discovery_lock import discovery_lock
from app.services.job_quality import enrich_job, eligibility, parse_date, now_iso, current_plan
from app.services.portfolio_service import candidate_profile


def match_context(user, resume, job):
    from app.services.job_mapping import job_to_extraction
    from app.services.recommendation_policy import POLICY_VERSION
    data = {'policy_version': POLICY_VERSION, 'candidate': candidate_profile(user, resume), 'job': job.raw_input_text,
            'requirements': job.requirements, 'plan': current_plan(job, user),
            'state': (job.research or {}).get('state'), 'structured_job': job_to_extraction(job).model_dump()}
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def process_user_backlog(db, user):
    from app.services.browser_policy import browser_session
    settings = get_settings()
    # One browser shared by this pass's renders, with a cap so a handful of slow
    # JS-rendered pages cannot stretch one pass into many minutes.
    with browser_session(max_renders=settings.rendered_fetches_per_pass):
        return _process_user_backlog(db, user, settings)


def _needs_original(job, settings):
    from app.services.original_posting import is_aggregator
    research = job.research or {}
    return (bool(settings.tavily_api_key) and is_aggregator(job.source_url)
            and research.get('verification_status') != 'page_checked' and not research.get('original_lookup_at'))


def _follow_to_original(job):
    """Swap an unverifiable aggregator copy for the employer's own posting, then re-check
    it there. The aggregator URL is kept in provenance; identity reconciliation afterwards
    merges it with any copy of the same posting already stored."""
    from app.services.original_posting import find_original_posting
    research = dict(job.research or {})
    research['original_lookup_at'] = now_iso()
    try:
        original = find_original_posting(job.title, job.company)
    except Exception as exc:
        research['original_lookup_error'] = str(exc)[:300]
        job.research = research
        return
    if not original:
        job.research = research
        return
    research['aggregator_url'] = job.source_url
    research.pop('retrieval_error', None)
    job.research = research
    job.source_url = original
    enrich_job(job)


def _search_waiting(db, user_id):
    from app.models.crawl_run import CrawlRun
    return db.scalar(select(CrawlRun.id).where(CrawlRun.user_id == user_id, CrawlRun.status == 'queued').limit(1)) is not None


def _process_user_backlog(db, user, settings):
    from app.services.match_service import score_and_store
    import time
    started = time.monotonic()
    resume = db.scalar(select(Resume).where(Resume.user_id == user.id, Resume.is_primary.is_(True), Resume.parse_status == 'parsed'))
    # Bound each pass; oldest unprocessed jobs are not permanently starved by new crawls.
    jobs = list(db.scalars(select(Job).where(Job.user_id == user.id).order_by(Job.updated_at.asc()).limit(1000)))
    now = datetime.now(timezone.utc)
    enriched = scored = score_attempts = lookups = 0
    skills = (resume.structured_profile or {}).get('skills', []) if resume else []
    def priority(job):
        hay = f'{job.title} {job.raw_input_text}'.lower()
        return sum(1 for skill in skills if skill.lower() in hay)
    jobs.sort(key=priority, reverse=True)
    for job in jobs:
        # Yield the user lock: a queued search for this user should not wait behind a
        # long enrichment pass, and remaining jobs are picked up by the next pass.
        if time.monotonic() - started > settings.backlog_pass_seconds or _search_waiting(db, user.id):
            break
        research = dict(job.research or {})
        retry_after = parse_date(research.get('retry_after'))
        if retry_after and retry_after > now:
            continue
        deadline = parse_date(research.get('deadline'))
        if deadline and deadline < now:
            research['state'] = 'expired'
            job.research = research
        rejected, concerns = eligibility(job, user.preferences or {}, current_plan(job, user))
        # Re-check closed listings periodically, but never score/notify them as active.
        last_checked = parse_date(research.get('last_attempt_at')) or parse_date(research.get('last_verified_at'))
        from app.services.recommendation_policy import POLICY_VERSION
        stale = (research.get('evidence_version') != POLICY_VERSION or not last_checked or last_checked < now - timedelta(days=1)
                 or research.get('application_link_status') == 'deferred')
        cheap_rejected = [reason for reason in rejected if reason in ('Excluded company', 'Excluded keyword', 'Seniority does not match', 'Employment type does not match')]
        if cheap_rejected:
            job.research = {**research, 'exclusion_reasons': rejected, 'eligibility_concerns': concerns}
            db.commit()
            continue
        if (not rejected and job.extraction_status == 'extracted' and not stale and lookups < settings.original_lookups_per_pass
                and enriched < settings.enrichment_batch_size and _needs_original(job, settings)):
            # Already checked and unverifiable on the aggregator: look for the employer's copy now.
            lookups += 1
            enriched += 1
            try:
                _follow_to_original(job)
                from app.services.discovery_store import reconcile_identity
                reconcile_identity(db, job)
                db.commit()
            except Exception as exc:
                db.rollback()
                job.research = {**research, 'original_lookup_at': now_iso(), 'original_lookup_error': str(exc)[:300]}
                db.commit()
        elif enriched < settings.enrichment_batch_size and (job.extraction_status != 'extracted' or stale):
            enriched += 1
            try:
                enrich_job(job)
                if lookups < settings.original_lookups_per_pass and _needs_original(job, settings):
                    lookups += 1
                    _follow_to_original(job)
                from app.services.discovery_store import reconcile_identity
                reconcile_identity(db, job)
                if job.extraction_status == 'failed':
                    job.research = {**job.research, 'retry_after': (now + timedelta(hours=settings.discovery_retry_hours)).isoformat()}
                db.commit()
            except Exception as exc:
                # One unsavable posting must not abort the rest of this user's pass.
                db.rollback()
                job.extraction_status = 'failed'
                job.research = {**research, 'enrichment_state': 'failed', 'enrichment_error': str(exc)[:400],
                                'retry_after': (now + timedelta(hours=settings.discovery_retry_hours)).isoformat()}
                db.commit()
                continue
        rejected, concerns = eligibility(job, user.preferences or {}, current_plan(job, user))
        job.research = {**(job.research or {}), 'exclusion_reasons': rejected, 'eligibility_concerns': concerns}
        if rejected or not resume or job.extraction_status != 'extracted' or score_attempts >= settings.scoring_batch_size:
            db.commit()
            continue
        existing = db.scalar(select(Match).where(Match.job_id == job.id, Match.resume_id == resume.id))
        context = match_context(user, resume, job)
        if existing and existing.context_hash == context:
            db.commit()
            continue
        score_attempts += 1
        try:
            score_and_store(db, job, resume)
            scored += 1
            job.research = {**job.research, 'retry_after': None, 'scoring_error': None}
            db.commit()
        except Exception as exc:
            db.rollback()
            job.research = {**(job.research or {}), 'scoring_error': str(exc)[:400],
                            'retry_after': (now + timedelta(hours=settings.discovery_retry_hours)).isoformat()}
            db.commit()
    return {'enriched': enriched, 'scored': scored}


_backlog_pool = None


def _pool():
    global _backlog_pool
    if _backlog_pool is None:
        from app.services.work_pool import WorkPool
        _backlog_pool = WorkPool('backlog', get_settings().backlog_workers)
    return _backlog_pool


def _process_user(user_id):
    with discovery_lock(user_id) as acquired:
        if not acquired:
            return
        with SessionLocal() as db:
            try:
                process_user_backlog(db, db.get(User, user_id))
            except Exception:
                db.rollback()
                import logging
                logging.getLogger(__name__).exception('Backlog failed for %s', user_id)


def process_backlogs():
    """Dispatch one bounded pass per user to the worker pool; users run concurrently,
    so one user's slow pages never hold up anyone else's results."""
    with discovery_lock('backlog-worker') as acquired:
        if not acquired:
            return
        with SessionLocal() as db:
            ids = list(db.scalars(select(User.id)))
        pool = _pool()
        for user_id in ids:
            pool.submit(user_id, _process_user, user_id)
