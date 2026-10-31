import re

from lxml import html as lxml_html

from app.ai.schemas.job_extraction_schema import JobExtraction
from app.models.job import Job

_NULL_LIKE = {"null", "none", "n/a", "na", "unknown", ""}
_HAS_TAGS = re.compile(r"<[a-zA-Z/][^>]*>")
_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Generic mailbox-provider addresses in a job posting are almost never "apply here" -
# they're usually a stray contact mention elsewhere on the page. Prefer a company-looking
# address and otherwise don't guess.
_GENERIC_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}


def extract_email_from_text(text: str | None) -> str | None:
    """Cheap regex fallback for crawled jobs, which never run the AI extraction prompt
    that would otherwise pull this out - still worth catching cases like a company's
    careers page listing "careers@company.com" in its footer/contact section."""
    if not text:
        return None
    for match in _EMAIL.finditer(text):
        email = match.group(0)
        if email.split("@")[-1].lower() not in _GENERIC_EMAIL_DOMAINS:
            return email
    return None


# Text that was UTF-8 but got decoded as Windows-1252/Latin-1 upstream ("Â£" for "£",
# "â€“" for "–"). Each candidate is a lead character plus the exact number of
# continuation characters its UTF-8 byte pattern needs.
_CONT = "\u0080-¿ŒœŠšŸŽžƒˆ˜–—‘-‚“-„†-•…‰‹›€™"
_MOJIBAKE = re.compile(
    f"[Â-ß][{_CONT}]|[à-ï][{_CONT}]{{2}}|[ð-ô][{_CONT}]{{3}}"
)


def _to_byte(ch: str) -> int:
    if ord(ch) < 256:
        return ord(ch)
    return ch.encode("cp1252")[0]


def _unmangle(match: re.Match) -> str:
    chunk = match.group(0)
    try:
        return bytes(_to_byte(c) for c in chunk).decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return chunk


def repair_text(value: str | None) -> str | None:
    """Undo double-decoded UTF-8. Only sequences that decode to valid UTF-8 change."""
    if not value or not _MOJIBAKE.search(value):
        return value
    return _MOJIBAKE.sub(_unmangle, value)


def html_to_text(raw: str | None) -> str:
    return _html_to_text(repair_text(raw))


def _html_to_text(raw: str | None) -> str:
    """Job board APIs (RemoteOK, Remotive) return the posting body as raw HTML. Convert
    it to clean, readable plain text - preserving paragraph/list breaks as newlines - so
    the full original posting can be shown on the job detail page without rendering
    untrusted HTML in the browser."""
    if not raw:
        return ""
    if not _HAS_TAGS.search(raw):
        return raw.strip()

    try:
        tree = lxml_html.fromstring(raw)
    except Exception:
        return raw.strip()

    for node in tree.xpath(".//script | .//style | .//noscript"):
        node.drop_tree()
    for br in tree.xpath(".//br"):
        br.tail = "\n" + (br.tail or "")
    block_tags = ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr")
    for el in tree.iter(*block_tags):
        el.tail = "\n" + (el.tail or "")

    text = tree.text_content()
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned


def clean_optional_text(value: str | None) -> str | None:
    """Some models emit the literal text "null"/"N/A" instead of a true null for an
    unset optional field, even when the schema already allows null. Normalize those
    placeholder strings back to None so they don't leak into the DB, UI, or filters."""
    if value is None:
        return None
    cleaned = value.strip()
    return None if cleaned.lower() in _NULL_LIKE else cleaned


def job_to_extraction(job: Job) -> JobExtraction:
    return JobExtraction(
        **{k: v for k, v in (job.research or {}).items() if k in JobExtraction.model_fields and k not in {"title", "company", "location", "salary_range", "employment_type", "work_mode", "requirements", "description_summary"}},
        title=job.title or "",
        company=job.company or "",
        location=job.location,
        salary_range=job.salary_range,
        employment_type=job.employment_type,
        work_mode=job.work_mode,
        requirements=job.requirements or [],
        # Crawled jobs never run the AI extraction pipeline, so description_text is always
        # None for them - fall back to the full original posting so the match scorer isn't
        # working off nothing but a title and company name.
        description_summary=(job.raw_input_text or job.description_text or "")[:40000],
    )
