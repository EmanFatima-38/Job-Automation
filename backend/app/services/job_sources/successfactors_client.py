from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright
from app.services.browser_policy import protect_page


class SuccessFactorsRequestError(Exception):
    pass


def _job_req_id(href: str) -> str | None:
    params = parse_qs(urlparse(href).query)
    values = params.get("career_job_req_id")
    return values[0] if values else None


def search_successfactors(listing_url: str, company_name: str, limit: int = 15) -> list[dict]:
    """SAP SuccessFactors is a common enterprise ATS/careers platform. Job titles on the
    listing page are real anchors with real hrefs (career_job_req_id query param) - no
    click-through tricks needed, just harvest and visit each one directly."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(user_agent="Mozilla/5.0 (compatible; ApplyPilotBot/1.0)")
                protect_page(page)
                page.goto(listing_url, timeout=25000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                anchors = page.eval_on_selector_all(
                    "a",
                    "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))",
                )
                postings: dict[str, str] = {}
                for a in anchors:
                    if a["href"] and "career_job_req_id" in a["href"] and a["text"]:
                        postings.setdefault(a["href"], a["text"])

                results = []
                for href, title in list(postings.items())[:limit]:
                    try:
                        page.goto(href, timeout=20000, wait_until="domcontentloaded")
                        page.wait_for_timeout(1500)
                        text = page.inner_text("body")
                    except Exception:
                        text = title

                    idx = text.find(title)
                    description = text[idx:] if idx != -1 else text
                    # The href carries a per-page-load session token (_s.crb=...) that
                    # changes every visit - using the full URL as external_id would both
                    # overflow the DB column and break dedup across crawls (same job would
                    # look "new" every time). The career_job_req_id is the one stable part.
                    req_id = _job_req_id(href) or href[:200]
                    results.append(
                        {
                            "external_id": f"successfactors:{company_name}:{req_id}",
                            "source": "successfactors",
                            "title": title,
                            "company": company_name,
                            "location": None,
                            "salary_range": None,
                            "employment_type": None,
                            "work_mode": None,
                            "url": href,
                            "description": description,
                        }
                    )
                return results
            finally:
                browser.close()
    except Exception as e:
        raise SuccessFactorsRequestError(
            f"SuccessFactors careers page request failed for {company_name}: {e}"
        ) from e
