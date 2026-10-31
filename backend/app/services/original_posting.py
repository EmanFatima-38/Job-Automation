"""Find the employer's own copy of a job found on an aggregator.

Aggregators (Jooble, LinkedIn, beBee, Indeed, ...) usually block automated checks or
only show a snippet, so a posting found there can never be verified, even when the job
is real. The employer's own careers page or ATS posting usually can be. This looks it up
once per job with one web search and accepts only a page on the company's own domain or
on an ATS board carrying the company's name; the result still goes through the normal
verification checks, so nothing is trusted from the search itself."""
import re
from urllib.parse import urlsplit

from app.services.job_sources.company_discovery import _is_denylisted, _looks_like_companys_own_domain, _normalize

AGGREGATOR_HOSTS = (
    'jooble.', 'linkedin.com', 'bebee.com', 'indeed.', 'glassdoor.', 'rozee.pk', 'ziprecruiter.', 'talent.com',
    'jobrapido.', 'careerjet.', 'simplyhired.', 'yourcareerhunter.com', 'mustakbil.com', 'jobz.pk', 'bayt.com',
    'naukri.', 'monster.', 'adzuna.', 'jora.', 'whatjobs.', 'jobsora.', 'trabajo.org', 'learn4good.',
)
ATS_HOSTS = ('greenhouse.io', 'lever.co', 'workable.com', 'ashbyhq.com', 'bamboohr.com', 'recruitee.com', 'breezy.hr',
             'smartrecruiters.com', 'teamtailor.com', 'myworkdayjobs.com', 'zohorecruit.com', 'hirestream.io', 'jobvite.com')
_STOP = {'and', 'the', 'for', 'with', 'job', 'jobs', 'hiring', 'remote', 'onsite', 'hybrid', 'full', 'time', 'part'}


def is_aggregator(url: str | None) -> bool:
    host = (urlsplit(url or '').hostname or '').lower()
    return any(h in host for h in AGGREGATOR_HOSTS)


def _title_words(title: str) -> set[str]:
    return {w for w in re.findall(r'[a-z][a-z+#]{1,}', (title or '').lower()) if w not in _STOP}


def _employer_page(url: str, company: str) -> bool:
    if not url or is_aggregator(url) or _is_denylisted(url):
        return False
    parts = urlsplit(url)
    host = (parts.hostname or '').lower()
    if any(host == h or host.endswith('.' + h) for h in ATS_HOSTS):
        # ATS boards are shared by many employers: the company must be named in the URL.
        name = _normalize(company)
        return len(name) >= 3 and name[:8] in _normalize(host + parts.path)
    return _looks_like_companys_own_domain(company, url)


def _role_link_on(index_url: str, words: set[str], company: str, fetch) -> str | None:
    """On the employer's careers index, find the link to this specific role."""
    from urllib.parse import urljoin
    from lxml import html as lxml_html
    try:
        page, final_url = fetch(index_url)
        tree = lxml_html.fromstring(page)
    except Exception:
        return None
    best, best_overlap = None, 0
    for a in tree.xpath('//a[@href]'):
        url = urljoin(final_url, a.get('href'))
        overlap = len(words & _title_words(a.text_content()))
        if overlap > best_overlap and urlsplit(url).scheme in ('http', 'https') and url.rstrip('/') != final_url.rstrip('/'):
            best, best_overlap = url, overlap
    if best and best_overlap >= max(1, min(2, len(words))) and (_employer_page(best, company) or urlsplit(best).hostname == urlsplit(final_url).hostname):
        return best
    return None


def find_original_posting(title: str | None, company: str | None, search=None, fetch=None) -> str | None:
    words = _title_words(title)
    if not company or len(words) < 1 or (title or '').strip().lower() in ('job', 'jobs', 'vacancy'):
        return None  # Nothing specific enough to search for.
    if search is None:
        from app.services.job_sources.tavily_client import tavily_search as search
    if fetch is None:
        from app.services.safe_fetch import fetch_public_page as fetch
    # Company first: a quoted full title mostly returns other employers' similar roles.
    results = search(f'{company.strip()} careers {title.strip()}', max_results=8, search_depth='basic')
    careers_index = None
    for result in results:
        url = result.get('url') or ''
        if not _employer_page(url, company):
            continue
        # The page has to be about this role, not just the company's careers index.
        overlap = words & _title_words(f"{result.get('title', '')} {(result.get('content') or '')[:600]}")
        if len(overlap) >= max(1, min(2, len(words))) and not re.search(r'(?i)/(careers?|jobs)/?$', urlsplit(url).path):
            return url
        careers_index = careers_index or url
    if careers_index:
        return _role_link_on(careers_index, words, company, fetch)
    return None
