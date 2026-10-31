from playwright.sync_api import sync_playwright
from app.services.browser_policy import protect_page


class WorkableRequestError(Exception):
    pass


def search_workable(company_slug: str, company_name: str, limit: int = 10) -> list[dict]:
    """Workable is a common ATS platform used by many companies for their careers page
    (e.g. apply.workable.com/{slug}/). Job cards have no visible-text anchor - the link is
    an invisible overlay <a href="/{slug}/j/{id}/"> with no innerText, positioned over each
    card - so title (inner_text, "Title" line followed by a "Posted ... ago" line) and
    detail URL (anchors matching "/j/") are extracted separately and paired by list order,
    which matches the page's visual order 1:1."""
    listing_url = f"https://apply.workable.com/{company_slug}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(user_agent="Mozilla/5.0 (compatible; ApplyPilotBot/1.0)")
                protect_page(page)
                page.goto(listing_url, timeout=25000, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)

                anchors = page.eval_on_selector_all(
                    "a", "els => els.map(e => e.href).filter(h => h.includes('/j/'))"
                )
                text = page.inner_text("body")
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                titles = [
                    lines[i] for i in range(len(lines) - 1) if lines[i + 1].startswith("Posted ")
                ]

                pairs = list(zip(titles, anchors))[:limit]
                results = []
                for title, url in pairs:
                    try:
                        page.goto(url, timeout=20000, wait_until="domcontentloaded")
                        page.wait_for_timeout(1500)
                        description = page.inner_text("body")
                    except Exception:
                        description = title
                    results.append(
                        {
                            "external_id": f"workable:{company_slug}:{url}",
                            "source": "workable",
                            "title": title,
                            "company": company_name,
                            "location": None,
                            "salary_range": None,
                            "employment_type": None,
                            "work_mode": None,
                            "url": url,
                            "description": description,
                        }
                    )
                return results
            finally:
                browser.close()
    except Exception as e:
        raise WorkableRequestError(f"Workable careers page request failed for {company_name}: {e}") from e
