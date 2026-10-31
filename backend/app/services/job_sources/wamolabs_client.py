from playwright.sync_api import sync_playwright
from app.services.browser_policy import protect_page

LISTING_URL = "https://www.wamolabs.com/careers"


class WamoLabsRequestError(Exception):
    pass


def search_wamolabs(limit: int = 10) -> list[dict]:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page(user_agent="Mozilla/5.0 (compatible; ApplyPilotBot/1.0)")
                protect_page(page)
                page.goto(LISTING_URL, timeout=30000, wait_until="networkidle")
                page.wait_for_timeout(2000)

                anchors = page.eval_on_selector_all(
                    "a",
                    "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))",
                )
                postings: dict[str, str] = {}
                for a in anchors:
                    href, text = a["href"], a["text"]
                    if "/careers/" in href and href.rstrip("/") != LISTING_URL and text and text != "Apply":
                        postings.setdefault(href, text)

                results = []
                for href, title in list(postings.items())[:limit]:
                    try:
                        page.goto(href, timeout=20000, wait_until="networkidle")
                        page.wait_for_timeout(1000)
                        text = page.inner_text("body")
                    except Exception:
                        text = title

                    idx = text.find(title)
                    description = text[idx:] if idx != -1 else text
                    results.append(
                        {
                            "external_id": f"wamolabs:{href}",
                            "source": "wamolabs",
                            "title": title,
                            "company": "Wamo Labs",
                            "location": "Lahore, Pakistan",
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
        raise WamoLabsRequestError(f"Wamo Labs careers page request failed: {e}") from e
