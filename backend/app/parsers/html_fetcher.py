import httpx
from app.services.safe_fetch import fetch_public_page
from lxml import html as lxml_html
from readability import Document


class JobFetchError(Exception):
    pass


def fetch_job_posting_text(url: str) -> str:
    try:
        page_html, _ = fetch_public_page(url)
    except Exception as e:
        raise JobFetchError(f"Could not fetch this URL ({e}).") from e

    try:
        summary_html = Document(page_html).summary()
        text = lxml_html.fromstring(summary_html).text_content()
    except Exception as e:
        raise JobFetchError(f"Could not extract readable content from this URL ({e}).") from e

    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not text:
        raise JobFetchError("Could not extract readable content from this URL.")

    return text
