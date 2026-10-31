import httpx


class RemoteOKRequestError(Exception):
    pass


def _format_salary(item: dict) -> str | None:
    lo = item.get("salary_min")
    hi = item.get("salary_max")
    if lo and hi:
        return f"${lo:,.0f} - ${hi:,.0f}"
    return None


def _map_employment_type(tags: list[str]) -> str | None:
    tags_lower = [t.lower() for t in tags]
    if any(t in tags_lower for t in ("internship", "intern")):
        return "internship"
    if any(t in tags_lower for t in ("part-time", "parttime", "part time")):
        return "part_time"
    if any(t in tags_lower for t in ("contract", "freelance")):
        return "contract"
    if any(t in tags_lower for t in ("full-time", "fulltime", "full time")):
        return "full_time"
    return None


def _matches(item: dict, keyword_terms: list[str]) -> bool:
    if not keyword_terms:
        return True
    haystack = " ".join(
        [
            str(item.get("position", "")),
            str(item.get("company", "")),
            " ".join(item.get("tags") or []),
        ]
    ).lower()
    # ALL words of the phrase must appear - matching on just one word (e.g. "ai" out of
    # "Agentic AI Developer") let through wildly unrelated postings like "Video Data
    # Annotator" or "AI Stockbroking App" that merely mention "AI" somewhere.
    return any(term in haystack for term in keyword_terms if len(term) > 2)


def search_remoteok(keywords: str, limit: int = 30) -> list[dict]:
    try:
        response = httpx.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "ApplyPilotBot/1.0 (job search aggregator)"},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise RemoteOKRequestError(f"RemoteOK request failed: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise RemoteOKRequestError(f"RemoteOK returned an unexpected response: {e}") from e

    # The first element of RemoteOK's feed is legacy metadata, not a job posting.
    items = [item for item in data if isinstance(item, dict) and item.get("id")]
    keyword_terms = [k.strip().lower() for k in keywords.split() if k.strip()]

    results = []
    for item in items:
        if not _matches(item, keyword_terms):
            continue
        results.append(
            {
                "external_id": f"remoteok:{item.get('id')}",
                "source": "remoteok",
                "posted_at": item.get("date"),
                "title": (item.get("position") or "").strip(),
                "company": item.get("company"),
                "location": item.get("location") or "Remote",
                "remote_eligibility": item.get("location"),
                "salary_range": _format_salary(item),
                "employment_type": _map_employment_type(item.get("tags") or []),
                "work_mode": "remote",
                "url": item.get("url") or f"https://remoteok.com/l/{item.get('id')}",
                "description": item.get("description", ""),
            }
        )
        if len(results) >= limit:
            break

    return results
