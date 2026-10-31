import hashlib
import json
from sqlalchemy import select, or_

from app.models.job import Job
from app.services.job_mapping import html_to_text, repair_text
from app.services.job_quality import canonical_url, fingerprint, now_iso, fit_column


def store_candidate(db, user_id, raw, plan):
    raw = {k: repair_text(v) if isinstance(v, str) and k not in ('url', 'external_id') else v for k, v in raw.items()}
    url = None if raw.get("shared_listing") else canonical_url(raw.get("url"))
    fp = fingerprint(raw.get('title'), raw.get('company'), raw.get('location'))
    external = raw['external_id']
    if len(external) > 255:
        external = external[:60] + ':' + hashlib.sha256(external.encode()).hexdigest()
    conditions = [Job.external_id == external]
    if url:
        conditions.append(Job.canonical_url == url)
    if fp:
        conditions.append(Job.fingerprint == fp)
    job = db.scalar(select(Job).where(Job.user_id == user_id, or_(*conditions)))
    created = job is None
    body = html_to_text(raw.get('description')) or raw.get('title') or ''
    digest = hashlib.sha256(body.encode()).hexdigest()
    if created:
        job = Job(user_id=user_id, source_type='crawl', external_id=external, source_url=raw.get('url'),
                  canonical_url=url, fingerprint=fp, raw_input_text=body, extraction_status='pending', requirements=[])
        db.add(job)
    research = dict(job.research or {})
    # Separate source snippet hash from enriched page hash to avoid endless rescoring.
    metadata_hash = hashlib.sha256(json.dumps({field: raw.get(field) for field in ('title', 'company', 'location', 'employment_type', 'work_mode', 'posted_at', 'remote_eligibility')}, sort_keys=True).encode()).hexdigest()
    metadata_changed = research.get('source_metadata_hash') != metadata_hash
    changed = research.get('source_content_hash') != digest or metadata_changed
    if changed:
        if created or len(body) >= len(job.raw_input_text or ''):
            job.raw_input_text = body
        for field in ('title', 'company', 'location', 'salary_range', 'employment_type', 'work_mode'):
            if raw.get(field):
                setattr(job, field, fit_column(field, raw[field]))
        research.update(source_content_hash=digest, source_metadata_hash=metadata_hash, content_updated_at=now_iso(), enrichment_state='pending')
        job.extraction_status = 'pending'
    research.setdefault('first_discovered_at', now_iso())
    research.update(last_seen_at=now_iso(), search_plan=plan, source=raw.get('source', 'unknown'))
    research['shared_listing'] = bool(raw.get('shared_listing'))
    if raw.get('discovered_from'):
        research['discovered_from'] = raw['discovered_from']
    sources = list(research.get('sources', []))
    provenance = {'source': raw.get('source'), 'id': external, 'url': raw.get('url')}
    if provenance not in sources:
        sources.append(provenance)
    research['sources'] = sources[:20]
    research.setdefault('state', 'unknown')
    research.setdefault('verification_status', 'unverified')
    if raw.get('posted_at'):
        research['posted_at'] = raw['posted_at']
        research['source_posted_at'] = raw['posted_at']
    if raw.get('application_url'):
        # Apply link published by the employer's own job-board feed: a candidate for the
        # reachability check when the rendered page hides its apply button. Still checked.
        research['feed_application_url'] = raw['application_url']
    if raw.get('remote_eligibility'):
        research['remote_eligibility'] = raw['remote_eligibility']
    job.research = research
    db.flush()  # next result in this batch can find the inserted identity
    return job, created


def reconcile_identity(db, job):
    """Mark enriched cross-source duplicates without deleting IDs or application history."""
    conditions = []
    if job.canonical_url:
        conditions.append(Job.canonical_url == job.canonical_url)
    if job.fingerprint:
        conditions.append(Job.fingerprint == job.fingerprint)
    if not conditions:
        return
    db.flush()
    original = db.scalar(select(Job).where(Job.user_id == job.user_id, or_(*conditions)).order_by(Job.created_at, Job.id))
    data = dict(job.research or {})
    if original and original.id != job.id:
        data['duplicate_of'] = str(original.id)
    else:
        data.pop('duplicate_of', None)
    job.research = data
