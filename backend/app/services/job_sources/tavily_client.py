import httpx

from app.config import get_settings

settings = get_settings()


class TavilyNotConfiguredError(Exception):
    pass


class TavilyRequestError(Exception):
    pass


def tavily_search(query: str, max_results: int = 8, search_depth: str = "advanced", *, start_date: str | None = None, exclude_domains: list[str] | None = None) -> list[dict]:
    if not settings.tavily_api_key:
        raise TavilyNotConfiguredError("Tavily API key is not configured")

    payload = {"query": query, "max_results": min(max_results, 20), "search_depth": search_depth}
    if start_date:
        payload['start_date'] = start_date
    if exclude_domains:
        payload['exclude_domains'] = exclude_domains
    try:
        response = httpx.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
            json=payload,
            timeout=20.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise TavilyRequestError(f"Tavily search failed: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise TavilyRequestError(f"Tavily returned an unexpected response: {e}") from e

    return data.get("results", [])

