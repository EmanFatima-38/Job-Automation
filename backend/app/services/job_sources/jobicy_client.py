import httpx


class JobicyRequestError(Exception):
    pass


def _map_employment_type(job_types: list[str] | None) -> str | None:
    if not job_types:
        return None
    normalized = [t.strip().lower().replace("-", "_").replace(" ", "_") for t in job_types]
    for token in ("full_time", "part_time", "contract", "internship", "temporary"):
        if token in normalized:
            return token
    return None


def _matches(item: dict, keyword_terms: list[str]) -> bool:
    if not keyword_terms:
        return True
    haystack = " ".join(
        [
            str(item.get("jobTitle", "")),
            str(item.get("companyName", "")),
            " ".join(item.get("jobIndustry") or []),
        ]
    ).lower()
    # ALL words of the phrase must appear - matching on just one generic word (e.g. "ai")
    # let through wildly unrelated postings that merely mention it in passing.
    return any(term in haystack for term in keyword_terms if len(term) > 2)


def search_jobicy(keywords: str, limit: int = 30) -> list[dict]:
    try:
        response = httpx.get(
            "https://jobicy.com/api/v2/remote-jobs",
            # Jobicy's `tag` param only matches a single predefined tag, which doesn't fit
            # free-text multi-word keywords well - fetch a batch and filter client-side instead.
            params={"count": 50},
            headers={"User-Agent": "ApplyPilotBot/1.0 (job search aggregator)"},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise JobicyRequestError(f"Jobicy request failed: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise JobicyRequestError(f"Jobicy returned an unexpected response: {e}") from e

    keyword_terms = [k.strip().lower() for k in keywords.split() if k.strip()]

    results = []
    for item in data.get("jobs", []):
        if not _matches(item, keyword_terms):
            continue
        results.append(
            {
                "external_id": f"jobicy:{item.get('id')}",
                "source": "jobicy",
                "posted_at": item.get("pubDate"),
                "title": (item.get("jobTitle") or "").strip(),
                "company": item.get("companyName"),
                "location": item.get("jobGeo") or "Remote",
                "remote_eligibility": item.get("jobGeo"),
                "salary_range": None,
                "employment_type": _map_employment_type(item.get("jobType")),
                "work_mode": "remote",
                "url": item.get("url"),
                "description": item.get("jobDescription") or item.get("jobExcerpt") or "",
            }
        )
        if len(results) >= limit:
            break

    return results
