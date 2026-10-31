import re
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from app.services.browser_policy import protect_page

from app.ai.discover_companies import extract_company_postings

_CAREERS_LINK_PATTERN = re.compile(r"career|jobs?\b|join us|join our team|work with us|open (?:positions|roles)|vacanc|hiring", re.I)
_CAREERS_PATH_PATTERN = re.compile(r"/(?:careers?|jobs?|join(?:-us)?|vacanc(?:y|ies)|openings|work-with-us|hiring)(?:[/?#._-]|$)", re.I)
# Pages that mention careers in passing (policies, articles) but never list openings.
_NEVER_CAREERS_PATTERN = re.compile(r"terms|privacy|legal|cookie|policy|blog|news|press|article|login|sign-?in|sign-?up", re.I)
# Sections that can host a careers sub-page (/about/careers) but are not one themselves.
_NOT_CAREERS_PATTERN = re.compile(r"/about|contact|faq|support", re.I)
_ATS_HOSTS = ("greenhouse.io", "lever.co", "workable.com", "bamboohr.com", "recruitee.com", "breezy.hr",
              "ashbyhq.com", "smartrecruiters.com", "hirestream.io", "teamtailor.com", "personio", "jobvite.com",
              "myworkdayjobs.com", "zohorecruit.com", "rippling.com")


class GenericCompanyScrapeError(Exception):
    pass


def _careers_score(text: str, href: str) -> int:
    """Rank a link as a careers page; 0 means not one. A matching path or an ATS host
    beats link text alone, and policy/about/blog pages are never chosen."""
    if not href or href.startswith(("mailto:", "tel:", "javascript:")):
        return 0
    parts = urlsplit(href)
    if parts.scheme not in ("http", "https"):
        return 0
    path = parts.path or "/"
    careers_path = bool(_CAREERS_PATH_PATTERN.search(path))
    if _NEVER_CAREERS_PATTERN.search(path) or (_NOT_CAREERS_PATTERN.search(path) and not careers_path):
        return 0
    host = (parts.hostname or "").lower()
    score = 0
    if any(host == h or host.endswith("." + h) or h in host for h in _ATS_HOSTS):
        score += 4
    if careers_path or host.startswith(("careers.", "jobs.")):
        score += 3
    if text and _CAREERS_LINK_PATTERN.search(text):
        score += 2
    return score


def _find_careers_url(page) -> str | None:
    anchors = page.eval_on_selector_all(
        "a", "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))"
    )
    best, best_score = None, 0
    for a in anchors:
        score = _careers_score(a.get("text") or "", a.get("href") or "")
        if score > best_score:
            best, best_score = a["href"], score
    return best


def _is_careers_page(url: str) -> bool:
    return _careers_score("", url) >= 3


def scrape_company(name: str, homepage_url: str, limit: int = 8) -> list[dict]:
    """Best-effort: visit a company's homepage, try to find and follow a careers link, then
    use the AI to pick out genuine job postings from whatever rendered there. Works without
    any company-specific code, but is less reliable than a hand-written scraper - some
    sites will legitimately yield nothing (no careers page, heavy anti-bot, etc.)."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(user_agent="Mozilla/5.0 (compatible; ApplyPilotBot/1.0)")
                protect_page(page)
                # "networkidle" hangs indefinitely on sites with persistent background
                # traffic (chat widgets, analytics beacons) - wait for the DOM instead and
                # give JS a fixed window to settle, which is far more resilient in practice.
                page.goto(homepage_url, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)

                if not _is_careers_page(page.url):
                    careers_url = _find_careers_url(page)
                    candidates = [careers_url] if careers_url else []
                    # No careers link on the page: try the conventional paths before giving up.
                    root = "{0.scheme}://{0.netloc}".format(urlsplit(page.url))
                    candidates += [root + "/careers", root + "/jobs"]
                    for candidate in candidates:
                        if candidate.rstrip("/") == page.url.rstrip("/"):
                            continue
                        try:
                            response = page.goto(candidate, timeout=20000, wait_until="domcontentloaded")
                            if response is not None and response.status >= 400:
                                continue
                            page.wait_for_timeout(2500)
                            if candidate == careers_url or _is_careers_page(page.url):
                                break
                        except Exception:
                            continue
                    else:
                        # Nothing that looks like a careers page: skip the AI extraction
                        # rather than reading postings out of a homepage or policy page.
                        return []

                page_text = page.inner_text("body")
                links = page.eval_on_selector_all(
                    "a", "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))"
                )
                links = [l for l in links if l["text"]][:60]

                postings = extract_company_postings(page_text, links).postings[:limit]

                results = []
                current_url = page.url
                for posting in postings:
                    description = page_text
                    job_url = posting.url or current_url
                    if posting.url and posting.url.rstrip("/") != current_url.rstrip("/"):
                        try:
                            page.goto(posting.url, timeout=15000, wait_until="domcontentloaded")
                            page.wait_for_timeout(1500)
                            description = page.inner_text("body")
                        except Exception:
                            description = page_text

                    idx = description.find(posting.title)
                    if idx != -1:
                        description = description[idx:]

                    results.append(
                        {
                            "external_id": f"company:{name}:{job_url}:{posting.title}",
                            "source": "discovered",
                            "shared_listing": not posting.url,
                            "title": posting.title,
                            "company": name,
                            "location": None,
                            "salary_range": None,
                            "employment_type": None,
                            "work_mode": None,
                            "url": job_url,
                            "description": description,
                        }
                    )
                return results
            finally:
                browser.close()
    except Exception as e:
        raise GenericCompanyScrapeError(f"Could not scrape {name} ({homepage_url}): {e}") from e
