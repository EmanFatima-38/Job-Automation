"""Public job-board feeds published by applicant-tracking systems (Workable, Greenhouse,
Lever, Ashby). One reusable client per platform: adding a company is one line in
crawl_service, no scraper. These are the JSON feeds the platforms publish for embedding a
company's openings, so they are fast (no browser), structured, and carry real posting
dates and locations."""
import html
from datetime import datetime, timezone

import httpx

from app.services.job_mapping import html_to_text

_HEADERS = {"User-Agent": "ApplyPilotBot/1.0 (job search aggregator)"}
# Company feeds list every office worldwide; keep the openings a candidate in Pakistan
# could take (local offices, or remote roles that name Pakistan).
PAKISTAN_TERMS = ("pakistan", "lahore", "karachi", "islamabad", "rawalpindi", "faisalabad", "peshawar", "multan")


class ATSFeedError(Exception):
    pass


def _get(url: str):
    try:
        response = httpx.get(url, headers=_HEADERS, timeout=20.0)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ATSFeedError(f"Job feed request failed ({url}): {exc}") from exc


def _in_region(*locations, country_code: str | None = None) -> bool:
    if (country_code or "").upper() == "PK":
        return True
    text = " ".join(str(l) for l in locations if l).lower()
    return any(term in text for term in PAKISTAN_TERMS)


def _employment_type(value: str | None) -> str | None:
    v = (value or "").lower().replace("-", "").replace("_", "").replace(" ", "")
    if "intern" in v:
        return "internship"
    if "parttime" in v:
        return "part_time"
    if "contract" in v or "freelance" in v:
        return "contract"
    if "temporary" in v:
        return "temporary"
    if "fulltime" in v:
        return "full_time"
    return None


def _work_mode(value: str | None, remote: bool = False) -> str | None:
    v = (value or "").lower().replace("-", "")
    if "hybrid" in v:
        return "hybrid"
    if remote or "remote" in v:
        return "remote"
    if "onsite" in v or "on site" in v or "office" in v:
        return "onsite"
    return None


def _iso(value) -> str | None:
    if not value:
        return None
    if isinstance(value, (int, float)):  # Lever: epoch milliseconds
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    return str(value)[:10]


def _job(source, external_id, title, company, location, url, description, *, employment=None,
         work_mode=None, posted_at=None, application_url=None):
    return {
        "external_id": external_id,
        "source": source,
        "title": (title or "").strip(),
        "company": company,
        "location": location or None,
        "salary_range": None,
        "employment_type": employment,
        "work_mode": work_mode,
        "url": url,
        "posted_at": posted_at,
        "application_url": application_url,
        "description": description,
    }


def search_workable_feed(slug: str, company: str, limit: int = 30) -> list[dict]:
    data = _get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    results = []
    for j in data.get("jobs", []):
        locations = [", ".join(filter(None, (l.get("city"), l.get("region"), l.get("country")))) for l in j.get("locations") or []]
        location = locations[0] if locations else ", ".join(filter(None, (j.get("city"), j.get("state"), j.get("country"))))
        if not _in_region(location, *locations):
            continue
        # Same URL/identity the browser scraper stored, so existing rows are matched.
        url = f"https://apply.workable.com/{slug}/j/{j['shortcode']}/"
        results.append(_job("workable", f"workable:{slug}:{url}", j.get("title"), company, location, url,
                            html_to_text(j.get("description")),
                            employment=_employment_type(j.get("employment_type")),
                            work_mode="remote" if j.get("telecommuting") else None,
                            posted_at=_iso(j.get("published_on")), application_url=j.get("application_url")))
    return results[:limit]


def search_greenhouse(slug: str, company: str, limit: int = 30) -> list[dict]:
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    results = []
    for j in data.get("jobs", []):
        location = (j.get("location") or {}).get("name", "")
        offices = [o.get("location") or o.get("name") for o in j.get("offices") or []]
        if not _in_region(location, *offices):
            continue
        results.append(_job("greenhouse", f"greenhouse:{slug}:{j['id']}", j.get("title"), j.get("company_name") or company,
                            location, j.get("absolute_url"), html_to_text(html.unescape(j.get("content") or "")),
                            work_mode=_work_mode(location),
                            # first_published is the real publish date; updated_at is not.
                            posted_at=_iso(j.get("first_published"))))
    return results[:limit]


def search_lever(slug: str, company: str, limit: int = 30) -> list[dict]:
    data = _get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    results = []
    for j in data if isinstance(data, list) else []:
        categories = j.get("categories") or {}
        locations = categories.get("allLocations") or [categories.get("location")]
        if not _in_region(*locations, country_code=j.get("country")):
            continue
        body = "\n\n".join(filter(None, (j.get("descriptionPlain"),
                                         *(f"{l.get('text', '')}\n{html_to_text(l.get('content'))}" for l in j.get("lists") or []),
                                         j.get("additionalPlain"))))
        results.append(_job("lever", f"lever:{slug}:{j['id']}", j.get("text"), company, ", ".join(filter(None, locations)),
                            j.get("hostedUrl"), body, employment=_employment_type(categories.get("commitment")),
                            work_mode=_work_mode(j.get("workplaceType")), posted_at=_iso(j.get("createdAt")),
                            application_url=j.get("applyUrl")))
    return results[:limit]


def search_ashby(slug: str, company: str, limit: int = 30) -> list[dict]:
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    results = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        address = ((j.get("address") or {}).get("postalAddress") or {})
        location = ", ".join(filter(None, (address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")))) or j.get("location")
        secondary = [s.get("location") for s in j.get("secondaryLocations") or [] if isinstance(s, dict)]
        if not _in_region(location, j.get("location"), *secondary):
            continue
        results.append(_job("ashby", f"ashby:{slug}:{j['id']}", j.get("title"), company, location, j.get("jobUrl"),
                            j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml")),
                            employment=_employment_type(j.get("employmentType")),
                            work_mode=_work_mode(j.get("workplaceType"), remote=bool(j.get("isRemote"))),
                            posted_at=_iso(j.get("publishedAt")), application_url=j.get("applyUrl")))
    return results[:limit]


FEEDS = {"workable": search_workable_feed, "greenhouse": search_greenhouse, "lever": search_lever, "ashby": search_ashby}
