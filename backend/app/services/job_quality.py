import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import httpx
from lxml import html as lxml_html

from app.ai.extract_job import extract_job
from app.services.vacancy_evidence import page_kind, clean_page, specific_vacancy, application_link, is_training_program
from app.services.recommendation_policy import POLICY_VERSION, remote_restriction, mandatory_evidence
from app.services.safe_fetch import fetch_public_page
from app.services.browser_policy import fetch_rendered_page, RenderBudgetExhausted
from app.services.job_mapping import html_to_text


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    p = urlsplit(url)
    if p.scheme not in ('http', 'https') or not p.hostname:
        return None
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid', '_s.crb')]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/') or '/', urlencode(sorted(query)), ''))


def fingerprint(title, company, location):
    if not title or not company or not location:
        return None
    text = '|'.join(re.sub(r'[^\w]+', ' ', s.lower()).strip() for s in (company, title, location))
    return hashlib.sha256(text.encode()).hexdigest()


def parse_date(value):
    try:
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
    except (ValueError, TypeError):
        return None


def date_has_evidence(value, text):
    date = parse_date(value)
    if not date:
        return False
    variants = [date.strftime(fmt).lower() for fmt in ('%Y-%m-%d', '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y')]
    normalized = re.sub(r'\s+', ' ', text.lower())
    return any(v in normalized or v.replace(' 0', ' ') in normalized for v in variants)


def jsonld_job(html):
    try:
        tree = lxml_html.fromstring(html)
    except Exception:
        return {}
    def visit(value):
        if isinstance(value, list):
            for item in value:
                found = visit(item)
                if found:
                    return found
        elif isinstance(value, dict):
            kind = value.get('@type', [])
            if kind == 'JobPosting' or isinstance(kind, list) and 'JobPosting' in kind:
                return value
            return visit(value.get('@graph', []))
        return {}
    for text in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            found = visit(json.loads(text))
            if found:
                return found
        except (ValueError, TypeError):
            continue
    return {}


def fit_column(field, value):
    """Clip free-text model/source output to the column width ("$190,500 USD annually (US);
    ..." overflowed salary_range and aborted the whole backlog pass)."""
    from app.models.job import Job
    length = getattr(Job.__table__.columns[field].type, 'length', None)
    if isinstance(value, str) and length and len(value) > length:
        return value[:length - 1].rstrip() + '…'
    return value


def enrich_job(job):
    """Shared enrichment; compatibility states remain pending/extracting/extracted/failed."""
    research = dict(job.research or {})
    research.setdefault('first_discovered_at', now_iso())
    research.update(enrichment_state='processing', last_attempt_at=now_iso())
    job.research = research
    job.extraction_status = 'extracting'
    metadata = {}
    page_retrieved = False
    # A shared_listing job's source_url is a company page hosting many postings, not this
    # one specifically (the generic scraper has no per-job deep link). Re-fetching it here
    # and overwriting raw_input_text/metadata-derived fields would collapse every distinct
    # posting found on that page into whichever one job the page happens to foreground -
    # keep the per-posting snippet captured at discovery time instead.
    shared_listing = bool(research.get('shared_listing'))
    if job.source_url:
        try:
            html, final_url = fetch_public_page(job.source_url)
            text = html_to_text(clean_page(html))
            # A static GET against a JS-rendered single-page app or a bot-protection
            # challenge shell (common on Workable/Greenhouse/Lever-style ATS platforms)
            # comes back as near-empty. Re-render once with a real browser rather than
            # treating that as proof the page itself is unreachable - a blocked static
            # fetch is not evidence of anything about the posting.
            if len(text) <= 100 and not shared_listing:
                try:
                    html, final_url = fetch_rendered_page(job.source_url)
                    text = html_to_text(clean_page(html))
                except RenderBudgetExhausted:
                    # Not evidence about the posting: leave it for a later pass rather
                    # than recording an unverified result (and skip the AI call).
                    research.update(enrichment_state='deferred', retry_after=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat())
                    job.research = research
                    job.extraction_status = 'pending'
                    return job
                except Exception:
                    pass
            metadata = jsonld_job(html) if not shared_listing else {}
            research['retrieved_url'] = final_url
            if len(text) > 100 and not shared_listing:
                job.raw_input_text = text[:60000]
            if not shared_listing:
                job.canonical_url = canonical_url(final_url)
            page_retrieved = bool(len(job.raw_input_text or '') > 100 or metadata) if shared_listing else bool(len(text) > 100 or metadata)
            if page_retrieved:
                research['last_verified_at'] = now_iso()
            research.pop('retrieval_error', None)
        except Exception as exc:
            research['retrieval_error'] = str(exc)[:400]
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (404, 410):
                research['state'] = 'closed'
    try:
        extraction = extract_job(job.raw_input_text[:40000])
        for field in ('title', 'company', 'location', 'salary_range', 'employment_type', 'work_mode', 'contact_email'):
            value = getattr(extraction, field)
            if value:
                setattr(job, field, fit_column(field, value))
        job.requirements = extraction.requirements
        job.description_text = extraction.description_summary
        research.update(extraction.model_dump(exclude_none=True, exclude={'title', 'company', 'location', 'salary_range', 'employment_type', 'work_mode', 'contact_email', 'requirements', 'description_summary'}))
        # Reliable JSON-LD wins over model suggestions. Do not infer missing dates.
        if metadata.get('title'):
            job.title = fit_column('title', str(metadata['title']))
        org = metadata.get('hiringOrganization')
        if isinstance(org, dict) and org.get('name'):
            job.company = fit_column('company', str(org['name']))
        for src, dst in [('datePosted', 'posted_at'), ('validThrough', 'deadline')]:
            if metadata.get(src):
                research[dst] = metadata[src]
        place = metadata.get('jobLocation')
        if isinstance(place, list):
            place = place[0] if place else None
        if isinstance(place, dict) and isinstance(place.get('address'), dict):
            address = place['address']
            location = ', '.join(str(address[k]) for k in ('addressLocality', 'addressRegion', 'addressCountry') if address.get(k))
            if location:
                job.location = fit_column('location', location)
        employment = metadata.get('employmentType')
        if isinstance(employment, list):
            employment = employment[0] if employment else None
        if isinstance(employment, str):
            mapped = {'FULL_TIME': 'full_time', 'PART_TIME': 'part_time', 'INTERN': 'internship', 'INTERNSHIP': 'internship', 'CONTRACTOR': 'contract', 'TEMPORARY': 'temporary'}
            job.employment_type = mapped.get(employment.upper(), job.employment_type)
        for field in ('posted_at', 'deadline'):
            value = research.get(field)
            reliable = metadata.get('datePosted' if field == 'posted_at' else 'validThrough')
            source_date = research.get('source_posted_at') if field == 'posted_at' else None
            if value and (not parse_date(value) or not (reliable or source_date == value or date_has_evidence(value, job.raw_input_text))):
                research[field] = None
        if metadata.get('applicantLocationRequirements'):
            research['remote_eligibility'] = json.dumps(metadata['applicantLocationRequirements'])
        if metadata.get('jobLocationType') == 'TELECOMMUTE':
            job.work_mode = 'remote'
        kind = page_kind(research.get('retrieved_url') or job.source_url or '')
        classification = extraction.is_job_posting
        if kind in ('directory', 'irrelevant') or is_training_program(job.raw_input_text):
            classification = False
        elif not page_retrieved:
            # A blocked fetch or short search snippet cannot establish non-vacancy.
            classification = None
        elif metadata:
            classification = True
        elif classification is False and specific_vacancy(job.raw_input_text, job.title, job.company):
            classification = None
            research['classification_concern'] = 'Vacancy evidence conflicts with model classification; review required'
        else:
            research.pop('classification_concern', None)
        is_vacancy = classification is True
        research['verification_status'] = 'page_checked' if page_retrieved and is_vacancy else 'unverified'
        research['is_job_posting'] = classification
        research['evidence_version'] = POLICY_VERSION
        application = canonical_url(research.get('application_url'))
        # The source URL remains available even when no distinct application link exists.
        if application and application not in (job.raw_input_text or '') and application not in locals().get('html', ''):
            application = None
        link = application_link(html, research.get('retrieved_url') or job.source_url) if page_retrieved else None
        if page_retrieved and not link and research.get('feed_application_url'):
            link = research['feed_application_url']
        research['application_url'] = link or job.canonical_url or job.source_url
        research['application_link_status'] = 'unverified'
        # Follow only a visible application anchor using the same public-network/robots policy.
        # A successful GET checks reachability, never submits an application.
        if page_retrieved and is_vacancy and link:
            try:
                if canonical_url(link) == canonical_url(research.get('retrieved_url')):
                    target_html, target_url = html, research['retrieved_url']
                else:
                    target_html, target_url = fetch_public_page(link)
                target_text = html_to_text(target_html)
                if len(target_text) <= 100:
                    # Same JS-rendered/bot-challenge shell problem can hit the distinct
                    # application page even when the posting page itself fetched fine.
                    target_html, target_url = fetch_rendered_page(link)
                    target_text = html_to_text(target_html)
                identifies_role = any(name and name.lower() in target_text.lower() for name in (job.title, job.company))
                if len(target_text) > 100 and identifies_role and not re.search(r'(?i)job (?:is )?no longer available|position (?:has been |is )?closed', target_text):
                    research['application_link_status'] = 'reachable'
                    research['application_url'] = target_url
            except RenderBudgetExhausted:
                research['application_link_status'] = 'deferred'
            except Exception as exc:
                research['application_link_error'] = str(exc)[:300]
        # A retrievable page alone does not prove an opening is still active. The model's
        # own application_available self-report is frequently null on ordinary pages (any
        # boilerplate reads as "conflicting evidence" to it) - a confirmed, independently
        # verified reachable application link is at least as strong a signal and must not
        # be ignored just because the model itself stayed uncertain.
        deadline = parse_date(research.get('deadline'))
        if deadline and deadline < datetime.now(timezone.utc):
            research['state'] = 'expired'
        elif page_retrieved and extraction.is_closed:
            research['state'] = 'closed'
        elif page_retrieved and is_vacancy and (extraction.application_available is True or research['application_link_status'] == 'reachable') and re.search(r'\b(apply|application|submit|send your (?:cv|resume))\b', job.raw_input_text, re.I):
            research['state'] = 'active'
        else:
            research['state'] = research.get('state') if research.get('state') in ('expired', 'closed') else 'unknown'
        research.update(enrichment_state='completed', enriched_at=now_iso())
        job.extraction_status = 'extracted'
        job.extraction_error = None
    except Exception as exc:
        research.update(enrichment_state='failed', enrichment_error=str(exc)[:400])
        job.extraction_status = 'failed'
        job.extraction_error = str(exc)[:400]
    research['content_hash'] = hashlib.sha256((job.raw_input_text or '').encode()).hexdigest()
    job.research = research
    job.fingerprint = fingerprint(job.title, job.company, job.location)
    return job


_ELIGIBILITY_PREFERENCES = {'employment_types', 'seniority', 'cities', 'countries', 'work_modes', 'remote',
                            'remote_country', 'max_age_days', 'excluded_companies', 'excluded_keywords'}


def preferences_hash(preferences: dict | None) -> str:
    """Identity of the saved preferences that affect eligibility (not notification or
    search-volume settings), recorded on each search plan when it is made."""
    from app.schemas.discovery import Preferences
    try:
        data = Preferences.model_validate(preferences or {}).model_dump(include=_ELIGIBILITY_PREFERENCES)
    except ValueError:
        data = {k: v for k, v in (preferences or {}).items() if k in _ELIGIBILITY_PREFERENCES}
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def current_plan(job, user) -> dict | None:
    """The search plan that found this job narrows eligibility only while the user's
    saved preferences are unchanged since that search. After the user edits them, the job
    is judged against the current preferences instead of an outdated search."""
    plan = (job.research or {}).get('search_plan')
    if plan and plan.get('preferences_hash') == preferences_hash(user.preferences):
        return plan
    return None


def eligibility(job, preferences: dict, plan: dict | None = None, profile: dict | None = None):
    """Return hard exclusion reasons separately from unknown eligibility concerns."""
    prefs = {**preferences}
    if plan:
        for key in ('employment_types', 'seniority', 'remote_country', 'max_age_days', 'work_modes'):
            if plan.get(key):
                prefs[key] = plan[key]
        if plan.get('locations'):
            prefs['cities'] = [x for x in plan['locations'] if not x.lower().startswith('remote')]
    research = job.research or {}
    rejected, concerns = [], []
    if research.get('duplicate_of'):
        rejected.append('Duplicate opportunity')
    haystack = f'{job.title or ""} {job.company or ""} {job.raw_input_text or ""}'.lower()
    if research.get('state') in ('closed', 'expired'):
        rejected.append('Posting is closed or expired')
    if research.get('is_job_posting') is False:
        rejected.append('Page is not an individual vacancy')
    if any(x.lower() in (job.company or '').lower() for x in prefs.get('excluded_companies', []) if x):
        rejected.append('Excluded company')
    if any(x.lower() in haystack for x in prefs.get('excluded_keywords', []) if x):
        rejected.append('Excluded keyword')
    types = prefs.get('employment_types', [])
    if types and job.employment_type and job.employment_type not in types:
        rejected.append('Employment type does not match')
    elif types and not job.employment_type:
        concerns.append('Employment type unknown')
    seniority = prefs.get('seniority', [])
    if any(x.lower() in ('entry level', 'entry-level', 'junior', 'intern') for x in seniority) and re.search(r'\b(senior|principal|staff|director|lead)\b', (job.title or '').lower()):
        rejected.append('Seniority does not match')
    if prefs.get('work_modes') and job.work_mode and job.work_mode not in prefs['work_modes']:
        rejected.append('Work mode does not match')
    elif prefs.get('work_modes') and not job.work_mode:
        concerns.append('Work mode unknown')
    if job.work_mode == 'remote':
        restriction = research.get('remote_eligibility') or ''
        country = prefs.get('remote_country', '')
        reason, concern = remote_restriction(restriction, country)
        if reason:
            rejected.append(reason)
        if concern:
            concerns.append(concern)
    elif prefs.get('cities') or prefs.get('countries'):
        if not job.location:
            concerns.append('Location unknown')
        elif not any(c.lower() in job.location.lower() for c in (prefs.get('cities') or prefs.get('countries', []))):
            rejected.append('Location does not match')
    deadline = parse_date(research.get('deadline'))
    if deadline and deadline < datetime.now(timezone.utc) and 'Posting is closed or expired' not in rejected:
        rejected.append('Posting deadline has passed')
    age = prefs.get('max_age_days')
    posted = parse_date(research.get('posted_at'))
    if age and posted and posted < datetime.now(timezone.utc) - timedelta(days=age):
        rejected.append('Older than requested posting window')
    elif age and not posted:
        concerns.append('Posting date unknown; requested freshness cannot be verified')
    if research.get('verification_status') != 'page_checked':
        concerns.append('Vacancy page has not been verified')
    if posted and posted > datetime.now(timezone.utc) + timedelta(days=1):
        concerns.append('Posting date is in the future; verify source evidence')
    if research.get('classification_concern'):
        concerns.append(research['classification_concern'])
    _, mandatory = mandatory_evidence(job, profile)
    concerns.extend(mandatory)
    return list(dict.fromkeys(rejected)), list(dict.fromkeys(concerns))
