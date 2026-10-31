import re

from playwright.sync_api import sync_playwright
from app.services.browser_policy import protect_page

LISTING_URL = "https://arbisoft.hirestream.io/careers/jobs/"
_TITLE_BEFORE_POSITION_COUNT = re.compile(r"^\d+\s+Position")


class ArbisoftRequestError(Exception):
    pass


def _extract_titles(listing_text: str) -> list[str]:
    """Hirestream (Arbisoft's ATS) renders each job card as a title line immediately
    followed by an "N Position(s)" line, with no real <a href> on the card itself - the
    card is click-driven, not a link. No JSON API either, so this text pattern is the
    only stable way to enumerate postings."""
    lines = [line.strip() for line in listing_text.splitlines() if line.strip()]
    titles = []
    for i, line in enumerate(lines[:-1]):
        if _TITLE_BEFORE_POSITION_COUNT.match(lines[i + 1]):
            titles.append(line)
    return titles


def search_arbisoft(limit: int = 10) -> list[dict]:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(user_agent="Mozilla/5.0 (compatible; ApplyPilotBot/1.0)")
                protect_page(page)
                page.goto(LISTING_URL, timeout=30000, wait_until="networkidle")
                page.wait_for_timeout(1500)
                titles = _extract_titles(page.inner_text("body"))[:limit]

                results = []
                for title in titles:
                    try:
                        page.goto(LISTING_URL, timeout=30000, wait_until="networkidle")
                        page.wait_for_timeout(1000)
                        page.get_by_text(title, exact=True).first.click(timeout=10000)
                        page.wait_for_timeout(2000)
                        detail_url = page.url
                        text = page.inner_text("body")
                    except Exception:
                        # One posting's card failing to open shouldn't lose the rest.
                        continue

                    idx = text.find(title)
                    description = text[idx:] if idx != -1 else text
                    results.append(
                        {
                            "external_id": f"arbisoft:{detail_url}",
                            "source": "arbisoft",
                            "title": title,
                            "company": "Arbisoft",
                            "location": "Lahore, Pakistan",
                            "salary_range": None,
                            "employment_type": None,
                            "work_mode": None,
                            "url": detail_url,
                            "description": description,
                        }
                    )
                return results
            finally:
                browser.close()
    except Exception as e:
        raise ArbisoftRequestError(f"Arbisoft careers page request failed: {e}") from e
