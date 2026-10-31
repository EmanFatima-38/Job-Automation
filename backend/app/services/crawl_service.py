import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.client import AIParseError, AIRefusalError
from app.config import get_settings
from app.database import SessionLocal
from app.models.crawl_run import CrawlRun
from app.models.discovered_company import DiscoveredCompany
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.services.job_sources.adzuna_client import (
    AdzunaNotConfiguredError,
    AdzunaRequestError,
    AdzunaUnsupportedCountryError,
    search_adzuna,
)
from app.services.job_sources.arbisoft_client import ArbisoftRequestError, search_arbisoft
from app.services.job_sources.company_discovery import discover_companies
from app.services.job_sources.generic_company_scraper import (
    GenericCompanyScrapeError,
    scrape_company,
)
from app.services.job_sources.jobicy_client import JobicyRequestError, search_jobicy
from app.services.job_sources.remoteok_client import RemoteOKRequestError, search_remoteok
from app.services.job_sources.remotive_client import RemotiveRequestError, search_remotive
from app.services.job_sources.successfactors_client import (
    SuccessFactorsRequestError,
    search_successfactors,
)
from app.services.job_sources.tavily_client import TavilyNotConfiguredError, TavilyRequestError
from app.services.job_sources.wamolabs_client import WamoLabsRequestError, search_wamolabs
from app.services.job_sources.workable_client import WorkableRequestError, search_workable
from app.services.job_mapping import extract_email_from_text, html_to_text
from app.services.match_service import score_and_store

settings = get_settings()

# Free, keyless remote-job sources tried on every crawl.
REMOTE_SOURCES = [
    ("remoteok", search_remoteok, RemoteOKRequestError),
    ("remotive", search_remotive, RemotiveRequestError),
    ("jobicy", search_jobicy, JobicyRequestError),
]

# Specific companies' own career pages, scraped directly (headless browser - these sites
# are JS-rendered SPAs with no public API). Each returns everything currently open at that
# company, unfiltered by role keyword - these are curated by name, not by search term.
# Only run for users based in/around Lahore (where these companies are) to avoid pointless
# browser-scraping time for users this list isn't relevant to.
COMPANY_SOURCES = [
    ("arbisoft", search_arbisoft, ArbisoftRequestError),
    ("wamolabs", search_wamolabs, WamoLabsRequestError),
]

# Companies hosted on a common ATS platform we've written a reusable client for - just
# needs the company's slug/URL on that platform, not a hand-written scraper per company.
# Each was confirmed (23 Oct 2026) to publish a live feed with Pakistan-based openings;
# feeds are filtered to Pakistan locations. Add a company with one line.
ATS_COMPANIES = [
    ("workable", "devsinc-17", "Devsinc"),
    ("greenhouse", "gomotive", "Motive"),
    ("greenhouse", "careem", "Careem"),
    ("lever", "educative", "Educative"),
    ("ashby", "tajir", "Tajir"),
]
SUCCESSFACTORS_COMPANIES = [
    (
        "https://career55.sapsf.eu/career?company=systemvent&career_ns=job_listing_summary&navBarLevel=JOB_SEARCH",
        "Systems Limited",
    ),
]

# Companies with no clean per-job link structure to hand-code against - fall back to the
# generic AI-assisted scraper (title + whatever text surrounds it on the listing page,
# since there's nothing clickable to fetch a full detail page from).
FIXED_GENERIC_COMPANIES = [
    ("Contour Software", "https://contour-software.com/jobs/"),
]

_LAHORE_HINTS = ("lahore", "pakistan")


def _wants_company_sources(user: User) -> bool:
    location = f"{user.city or ''} {user.country or ''}".strip().lower()
    return any(hint in location for hint in _LAHORE_HINTS)


# Companies discovered dynamically via web search (industry + city inferred from the
# user's resume), scraped with a generic (not hand-written per site) scraper. Less
# reliable than the hand-coded COMPANY_SOURCES above - some sites won't yield anything -
# but covers any company, not just ones we've manually added.
MAX_DISCOVERED_COMPANIES = 6
# Re-running discovery costs search API + AI calls; the scrape itself is free. Cache the
# discovered company list and only refresh it this often - every crawl in between just
# re-scrapes the same cached companies.
DISCOVERY_REFRESH_DAYS = 7


def _get_or_refresh_discovered_companies(db: Session, user: User) -> list[DiscoveredCompany]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=DISCOVERY_REFRESH_DAYS)
    cached = list(
        db.scalars(
            select(DiscoveredCompany).where(
                DiscoveredCompany.user_id == user.id,
                DiscoveredCompany.discovered_at >= cutoff,
            )
        )
    )
    if cached:
        return cached

    target_roles = [p.strip() for p in (user.search_keywords or "").split(",") if p.strip()]
    companies = discover_companies(
        target_roles, user.city, user.country, limit=MAX_DISCOVERED_COMPANIES
    )

    db.query(DiscoveredCompany).filter(DiscoveredCompany.user_id == user.id).delete()
    rows = [
        DiscoveredCompany(user_id=user.id, name=c["name"], homepage_url=c["homepage_url"])
        for c in companies
    ]
    db.add_all(rows)
    db.flush()
    return rows


class CrawlNotEnabledError(Exception):
    pass


class CrawlAlreadyRunningError(Exception):
    pass


def enqueue_search(db, user, intent='', force=False):
    from app.services.discovery_lock import discovery_lock
    with discovery_lock(f'enqueue:{user.id}') as acquired:
        if not acquired:
            raise CrawlAlreadyRunningError('Another search is being queued')
        active = db.scalar(select(CrawlRun).where(CrawlRun.user_id == user.id, CrawlRun.status.in_(['queued', 'running', 'cancelling'])))
        if active:
            return active
        run = CrawlRun(user_id=user.id, intent=intent, plan={'force': force}, status='queued',
                       started_at=datetime.now(timezone.utc), jobs_found=0, jobs_created=0, source_results=[])
        db.add(run)
        db.commit()
        db.refresh(run)
        return run


def rank_by_plan(results, plan):
    """Order a company feed's openings by overlap with the planned roles and skills, so the
    per-source budget keeps the most relevant ones instead of whatever the feed lists first."""
    import re
    terms = {w for phrase in (plan.roles + plan.skills) for w in re.findall(r'[a-z][a-z+#.]{1,}', phrase.lower())
             if w not in {'and', 'the', 'for', 'with', 'engineer', 'developer', 'senior', 'junior'}}
    patterns = [re.compile(r'(?<![a-z])' + re.escape(t) + r'(?![a-z])') for t in terms]
    def score(item):
        title = (item.get('title') or '').lower()
        body = (item.get('description') or '')[:3000].lower()
        return sum(3 for p in patterns if p.search(title)) + sum(1 for p in patterns if p.search(body))
    return sorted(results, key=score, reverse=True)


def _sources(db, user, plan, prefs):
    """All original adapters remain in the acquisition pipeline."""
    from app.services.job_sources.vacancy_search import search_vacancies
    roles = plan.roles[:4]
    limit = prefs.results_per_source
    for role in roles:
        if user.country:
            for page in range(1, 3 if prefs.search_depth == 'advanced' else 2):
                yield 'adzuna', role, lambda role=role, page=page: search_adzuna(user.country, role, user.city, limit, page)
        for name, fn, _ in REMOTE_SOURCES:
            yield name, role, lambda fn=fn, role=role: fn(role, limit=limit)
    if _wants_company_sources(user):
        for name, fn, _ in COMPANY_SOURCES:
            yield name, 'company', lambda fn=fn: fn(limit=limit)
        from app.services.job_sources.ats_feeds import FEEDS
        for platform, slug, name in ATS_COMPANIES:
            def feed(platform=platform, slug=slug, name=name):
                try:
                    return rank_by_plan(FEEDS[platform](slug, name, limit=200), plan)
                except Exception:
                    if platform != 'workable':
                        raise
                    # The JSON feed failed; the slower browser scraper reads the same board.
                    return search_workable(slug, name, limit=limit)
            yield name, 'company', feed
        for url, name in SUCCESSFACTORS_COMPANIES:
            yield name, 'company', lambda url=url, name=name: search_successfactors(url, name, limit=limit)
        for name, url in FIXED_GENERIC_COMPANIES:
            yield name, 'company', lambda name=name, url=url: scrape_company(name, url, limit=limit)
    # Dynamic discovery is global; fixed local companies retain their regional relevance.
    if settings.tavily_api_key:
        from datetime import date
        for query in plan.queries:
            for excluded in prefs.excluded_companies[:5]:
                query += ' -"' + excluded.replace('"', '') + '"'
            yield 'tavily', query, lambda query=query: search_vacancies(query, limit, prefs.search_depth, max_age_days=plan.max_age_days)
        def companies():
            rows = _get_or_refresh_discovered_companies(db, user)
            results = []
            errors = []
            for company in rows:
                try:
                    results.extend(scrape_company(company.name, company.homepage_url, limit=min(limit, 8)))
                except Exception as exc:
                    errors.append(str(exc))
            if errors:
                # Preserve successful results while exposing each failure to the caller.
                return results, '; '.join(errors)[:1000]
            return results
        yield 'discovered', 'companies', companies
    else:
        def missing_tavily():
            raise TavilyNotConfiguredError('Tavily key missing; general web discovery unavailable')
        yield 'tavily', 'configuration', missing_tavily


def execute_run(db, run):
    import logging
    from app.schemas.discovery import Preferences
    from app.services.discovery_lock import discovery_lock
    from app.services.search_planner import build_plan
    from app.services.portfolio_service import candidate_profile, refresh_portfolio
    from app.services.discovery_store import store_candidate
    with discovery_lock(run.user_id) as acquired:
        if not acquired:
            return run
        db.refresh(run)
        if run.status != 'queued':
            return run
        user = db.get(User, run.user_id)
        force = run.plan.get('force', False)
        run.status = 'running'
        run.started_at = datetime.now(timezone.utc)
        db.commit()
        try:
            resume = db.scalar(select(Resume).where(Resume.user_id == user.id, Resume.is_primary.is_(True), Resume.parse_status == 'parsed'))
            prefs = Preferences.model_validate(user.preferences or {})
            refresh_portfolio(db, user)
            plan = build_plan(user, candidate_profile(user, resume), run.intent)
            from app.services.job_quality import preferences_hash
            plan.preferences_hash = preferences_hash(user.preferences)
            run.plan = plan.model_dump()
            db.commit()
            recent = list(db.scalars(select(CrawlRun).where(CrawlRun.user_id == user.id,
                CrawlRun.id != run.id, CrawlRun.started_at >= datetime.now(timezone.utc) - timedelta(hours=6))))
            cooldown = {(r.get('source'), r.get('query')) for old in recent for r in old.source_results
                        if r.get('jobs_found') == 0 and not r.get('skipped')}
            results = []
            tasks = list(_sources(db, user, plan, prefs))
            per_source_budget = max(1, settings.discovery_max_jobs // max(1, len(tasks)))
            for source, query, fetch in tasks:
                db.refresh(run)
                if run.status == 'cancelling':
                    run.status = 'cancelled'
                    break
                if datetime.now(timezone.utc) - run.started_at.replace(tzinfo=timezone.utc) > timedelta(minutes=settings.discovery_run_timeout_minutes):
                    run.error_message = 'Run time budget reached; completed sources retained'
                    break
                if not force and (source, query) in cooldown:
                    results.append({'source': source, 'query': query, 'tier': 'cooldown', 'jobs_found': 0, 'error': None, 'skipped': True})
                    continue
                error = None
                raw = []
                try:
                    import time
                    for attempt in range(2):
                        try:
                            value = fetch()
                            break
                        except (AdzunaNotConfiguredError, AdzunaUnsupportedCountryError, TavilyNotConfiguredError):
                            raise
                        except Exception as exc:
                            if attempt or any(code in str(exc) for code in ('429', '403', '401')):
                                raise
                            time.sleep(1)
                    if isinstance(value, tuple):
                        raw, error = value
                    else:
                        raw = value
                except Exception as exc:
                    error = str(exc)[:1000]
                    db.rollback()
                found = len(raw)
                for item in raw[:per_source_budget]:
                    try:
                        with db.begin_nested():
                            _, created = store_candidate(db, user.id, item, plan.model_dump())
                        run.jobs_created += int(created)
                    except Exception as exc:
                        error = str(exc)[:500]
                run.jobs_found += found
                results.append({'source': source, 'query': query, 'tier': 'discovery', 'jobs_found': found, 'error': error})
                run.source_results = list(results)
                db.commit()
            db.refresh(run)
            if run.status == 'cancelling':
                run.status = 'cancelled'
            if run.status != 'cancelled':
                attempted = [r for r in results if not r.get('skipped')]
                errors = [r for r in attempted if r['error']]
                if attempted and len(errors) == len(attempted) and not run.jobs_found:
                    run.status = 'failed'
                elif errors or run.error_message or not attempted:
                    run.status = 'partial'
                else:
                    run.status = 'success'
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:
            db.rollback()
            logging.getLogger(__name__).exception('Discovery run failed')
            run.status = 'failed'
            run.error_message = str(exc)[:1000]
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
        db.refresh(run)
        return run


def run_crawl_for_user(db, user):
    return execute_run(db, enqueue_search(db, user))


def run_crawl_now(db, user):
    if not user.crawl_enabled:
        raise CrawlNotEnabledError('Crawling is not enabled for this profile')
    return run_crawl_for_user(db, user)


def list_crawl_runs(db, user_id, limit=20):
    return list(db.scalars(select(CrawlRun).where(CrawlRun.user_id == user_id).order_by(CrawlRun.started_at.desc()).limit(limit)))


_search_pool = None


def _pool():
    global _search_pool
    if _search_pool is None:
        from app.services.work_pool import WorkPool
        _search_pool = WorkPool('search', settings.search_workers)
    return _search_pool


def _execute_run_id(run_id):
    with SessionLocal() as db:
        run = db.get(CrawlRun, run_id)
        if run is not None:
            execute_run(db, run)


def process_search_queue():
    """Recover abandoned runs, then hand queued runs to the worker pool without waiting.
    Each run holds only its own user's lock, so a slow search delays nobody else."""
    from app.services.discovery_lock import discovery_lock
    with discovery_lock('search-queue') as acquired:
        if not acquired:
            return
        pool = _pool()
        with SessionLocal() as db:
            # An abandoned running record can be recovered only if no worker owns its user lock.
            for run in db.scalars(select(CrawlRun).where(CrawlRun.status.in_(['running', 'cancelling']))):
                if pool.busy(run.id):
                    continue
                with discovery_lock(run.user_id) as user_lock:
                    if user_lock:
                        run.status = 'cancelled' if run.status == 'cancelling' else 'interrupted'
                        run.error_message = 'Worker interrupted; completed results retained. A new search can be started.'
                        run.finished_at = datetime.now(timezone.utc)
            db.commit()
            ids = list(db.scalars(select(CrawlRun.id).where(CrawlRun.status == 'queued').order_by(CrawlRun.started_at).limit(50)))
        for run_id in ids:
            pool.submit(run_id, _execute_run_id, run_id)


def run_all_crawls():
    from app.services.discovery_lock import discovery_lock
    with discovery_lock('scheduled-discovery') as acquired:
        if not acquired:
            return
        with SessionLocal() as db:
            ids = list(db.scalars(select(User.id).where(User.crawl_enabled.is_(True))))
        for user_id in ids:
            with SessionLocal() as db:
                try:
                    latest = db.scalar(select(CrawlRun).where(CrawlRun.user_id == user_id).order_by(CrawlRun.started_at.desc()))
                    if latest and latest.started_at > datetime.now(timezone.utc) - timedelta(hours=settings.crawl_interval_hours):
                        continue
                    enqueue_search(db, db.get(User, user_id))
                except Exception:
                    db.rollback()
                    import logging
                    logging.getLogger(__name__).exception('Cannot schedule discovery for %s', user_id)



