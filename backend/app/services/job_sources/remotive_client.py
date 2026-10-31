import httpx


class RemotiveRequestError(Exception):
    pass


def _map_employment_type(job_type: str | None) -> str | None:
    if not job_type:
        return None
    normalized = job_type.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in ("full_time", "part_time", "contract", "internship", "temporary"):
        return normalized
    return None


def search_remotive(keywords: str, limit: int = 30) -> list[dict]:
    params: dict = {"limit": limit}
    if keywords:
        params["search"] = keywords

    try:
        response = httpx.get(
            "https://remotive.com/api/remote-jobs",
            params=params,
            headers={"User-Agent": "ApplyPilotBot/1.0 (job search aggregator)"},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise RemotiveRequestError(f"Remotive request failed: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise RemotiveRequestError(f"Remotive returned an unexpected response: {e}") from e

    results = []
    for item in data.get("jobs", [])[:limit]:
        results.append(
            {
                "external_id": f"remotive:{item.get('id')}",
                "source": "remotive",
                "posted_at": item.get("publication_date"),
                "title": (item.get("title") or "").strip(),
                "company": item.get("company_name"),
                "location": item.get("candidate_required_location") or "Remote",
                "remote_eligibility": item.get("candidate_required_location"),
                "salary_range": item.get("salary") or None,
                "employment_type": _map_employment_type(item.get("job_type")),
                "work_mode": "remote",
                "url": item.get("url"),
                "description": item.get("description") or "",
            }
        )
    return results
