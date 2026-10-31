"""Bounded vacancy discovery with native recency and directory expansion."""
import hashlib
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, urlsplit
from lxml import html as lxml_html
from app.services.job_sources.tavily_client import tavily_search
from app.services.safe_fetch import fetch_public_page
from app.services.vacancy_evidence import page_kind

EXCLUDED_DOMAINS = ['facebook.com', 'instagram.com', 'youtube.com', 'tiktok.com', 'pinterest.com', 'threads.com', 'twitter.com', 'x.com']


def directory_links(html, base, limit=6):
    try:
        tree = lxml_html.fromstring(html)
    except (ValueError, TypeError):
        return []
    rows, seen = [], set()
    for a in tree.xpath('//a[@href]'):
        url = urljoin(base, a.get('href'))
        p = urlsplit(url)
        title = ' '.join(a.text_content().split())[:200]
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.port not in (None, 80, 443):
            continue
        if page_kind(url) != 'candidate' or url in seen:
            continue
        if not re.search(r'(?i)/jobs?/|/positions?/|/requisitions?/|/j/|/posting/', p.path):
            continue
        if len(title) < 5 or re.fullmatch(r'(?i)(view|all|search|browse|find|open)\s+(jobs|positions|roles)', title):
            continue
        seen.add(url)
        rows.append({'url': url, 'title': title, 'content': title, 'discovered_from': base})
        if len(rows) >= limit:
            break
    return rows


def search_vacancies(query: str, limit: int = 10, depth: str = 'basic', max_age_days: int | None = None) -> list[dict]:
    suffix = re.search(r'\s+after:(\d{4}-\d{2}-\d{2})', query)
    start = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).date().isoformat() if max_age_days else suffix.group(1) if suffix else None
    query = re.sub(r'\s+after:\S+', '', query).strip()
    results = []
    for attempt in range(2):
        try:
            results = tavily_search(query, max_results=min(20, max(limit * 2, 6)), search_depth=depth,
                                    start_date=start, exclude_domains=EXCLUDED_DOMAINS)
            break
        except Exception as exc:
            if attempt or any(code in str(exc) for code in ('401', '403', '429', '432', '433')):
                raise
            time.sleep(1)
    candidates, directories = [], []
    for row in results:
        kind = page_kind(row.get('url', ''))
        if kind == 'candidate':
            candidates.append(row)
        elif kind == 'directory':
            directories.append(row)
    if len(candidates) < min(limit, 3):
        focused = query + ' apply (site:jobs.lever.co OR site:job-boards.greenhouse.io OR site:apply.workable.com OR site:careers.smartrecruiters.com)'
        try:
            more = tavily_search(focused, max_results=min(10, limit), search_depth=depth,
                                 start_date=start, exclude_domains=EXCLUDED_DOMAINS)
        except Exception:
            if not candidates and not directories:
                raise
            more = []  # Preserve successful broad-search hits if the optional fallback fails.
        for row in more:
            kind = page_kind(row.get('url', ''))
            if kind == 'candidate':
                candidates.append(row)
            elif kind == 'directory':
                directories.append(row)
    for directory in directories[:2]:
        if len(candidates) >= limit:
            break
        try:
            html, final = fetch_public_page(directory['url'])
            candidates.extend(directory_links(html, final, limit=limit - len(candidates)))
        except Exception:
            continue
    unique = {}
    for row in candidates:
        if row.get('url'):
            unique.setdefault(row['url'].split('#')[0], row)
    return [{'external_id': 'web:' + hashlib.sha256(url.encode()).hexdigest(),
             'source': 'tavily', 'url': url, 'title': r.get('title'),
             'description': r.get('content', ''), 'discovered_from': r.get('discovered_from'),
             'verification_status': 'unverified'} for url, r in list(unique.items())[:limit]]
