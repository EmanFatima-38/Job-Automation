import httpx

from app.config import get_settings

settings = get_settings()

# Countries Adzuna's public API covers. Notably absent: Pakistan and most of
# South/Central Asia outside India - searches for those fall through to RemoteOK.
ADZUNA_SUPPORTED_COUNTRIES = {
    "gb", "us", "at", "au", "br", "ca", "de", "fr", "in", "it",
    "nl", "nz", "pl", "ru", "sg", "za", "mx", "es", "se", "ch",
}


class AdzunaNotConfiguredError(Exception):
    pass


class AdzunaUnsupportedCountryError(Exception):
    pass


class AdzunaRequestError(Exception):
    pass


def is_country_supported(country_code: str) -> bool:
    return country_code.lower() in ADZUNA_SUPPORTED_COUNTRIES


def _format_salary(item: dict) -> str | None:
    lo = item.get("salary_min")
    hi = item.get("salary_max")
    if lo and hi:
        if lo == hi:
            return f"{lo:,.0f}"
        return f"{lo:,.0f} - {hi:,.0f}"
    return None


def _map_employment_type(item: dict) -> str | None:
    # Adzuna exposes two independent axes: contract_type (permanent|contract) and
    # contract_time (full_time|part_time). Contract status takes priority for our
    # single employment_type filter since it's the more specific classification.
    if item.get("contract_type") == "contract":
        return "contract"
    contract_time = item.get("contract_time")
    if contract_time in ("full_time", "part_time"):
        return contract_time
    return None


def _map_work_mode(item: dict) -> str | None:
    haystack = f"{item.get('title', '')} {(item.get('location') or {}).get('display_name', '')}".lower()
    if "remote" in haystack:
        return "remote"
    return None


def search_adzuna(
    country_code: str, keywords: str, where: str | None = None, results_per_page: int = 20, page: int = 1
) -> list[dict]:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        raise AdzunaNotConfiguredError("Adzuna API credentials are not configured")

    aliases = {'pakistan': 'pk', 'united states': 'us', 'usa': 'us', 'united kingdom': 'gb', 'uk': 'gb', 'india': 'in', 'canada': 'ca', 'germany': 'de', 'australia': 'au'}
    code = aliases.get(country_code.lower().strip(), country_code.lower().strip())
    if not is_country_supported(code):
        raise AdzunaUnsupportedCountryError(f"Adzuna does not support country '{country_code}'")

    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": results_per_page,
        "what": keywords,
        "content-type": "application/json",
    }
    if where:
        params["where"] = where

    try:
        response = httpx.get(
            f"https://api.adzuna.com/v1/api/jobs/{code}/search/{page}",
            params=params,
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise AdzunaRequestError(f"Adzuna request failed: {e}") from e

    data = response.json()
    results = []
    for item in data.get("results", []):
        results.append(
            {
                "external_id": f"adzuna:{item.get('id')}",
                "source": "adzuna",
                "posted_at": item.get("created"),
                "title": (item.get("title") or "").strip(),
                "company": (item.get("company") or {}).get("display_name"),
                "location": (item.get("location") or {}).get("display_name"),
                "salary_range": _format_salary(item),
                "employment_type": _map_employment_type(item),
                "work_mode": _map_work_mode(item),
                "url": item.get("redirect_url"),
                "description": item.get("description", ""),
            }
        )
    return results
