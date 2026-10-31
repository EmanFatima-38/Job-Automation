import re
from urllib.parse import urlparse

from app.ai.discover_companies import extract_company_names, infer_industry
from app.services.job_sources.tavily_client import tavily_search

# Domains that are never a company's own homepage - job boards, directories, listicle
# sites, and social media that show up constantly in "companies in <city>" searches.
_DENYLIST_DOMAINS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "rozee.pk", "bayt.com", "monster.com",
    "naukri.com", "jobz.pk", "mustakbil.com", "pakpositions.com", "facebook.com",
    "instagram.com", "twitter.com", "x.com", "youtube.com", "wikipedia.org", "github.com",
    "crunchbase.com", "zoominfo.com", "rocketreach.co", "techbehemoths.com",
    "revenuebase.ai", "designrush.com", "clutch.co", "d7leadfinder.com", "reddit.com",
    "simplilearn.com", "britannica.com", "geeksforgeeks.org", "softonic.com",
    "mapquest.com", "nucamp.co", "devsdata.com", "pnytrainings.com", "crossover.com",
    "clocate.com", "eventbrite.com", "10times.com", "bizzabo.com", "threads.com",
    "threads.net", "quora.com", "medium.com",
    # Sales-intelligence / company-data directories - these show up constantly for
    # "<company> official website" lookups but are never the company's actual site.
    "investing.com", "leadiq.com", "owler.com", "craft.co", "pitchbook.com", "dnb.com",
    "tracxn.com", "similarweb.com", "getlatka.com", "apollo.io", "bloomberg.com",
    "wellfound.com", "angel.co",
}


def _domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def _is_denylisted(url: str) -> bool:
    domain = _domain(url)
    return any(domain == d or domain.endswith("." + d) for d in _DENYLIST_DOMAINS)


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _looks_like_companys_own_domain(name: str, url: str) -> bool:
    """Business-data directories (ZoomInfo, Tracxn, RocketReach, random "business
    directory" sites, stock-ticker pages, ...) rank above a small company's actual site
    constantly - there's no finite denylist for all of them. Instead, prefer a result
    whose domain's own name actually resembles the company name (e.g. "arbisoft" in
    "arbisoft.hirestream.io", "systemsltd" vs "Systems Limited")."""
    base_label = _domain(url).split(".")[0]
    normalized_base = _normalize(base_label)
    normalized_name = _normalize(name)
    if len(normalized_base) < 3 or len(normalized_name) < 3:
        return False
    return (
        normalized_base in normalized_name
        or normalized_name in normalized_base
        or normalized_base[:5] == normalized_name[:5]
    )


def discover_companies(
    target_roles: list[str], city: str | None, country: str | None, limit: int = 6
) -> list[dict]:
    """Find real companies in the candidate's industry and city via web search, returning
    [{"name": ..., "homepage_url": ...}]. Two-step: first find companies mentioned in
    general "<industry> companies in <city>" search results (directories/listicles are
    fine here - we only need the names out of them), then a second targeted search per
    name to find that company's actual website (never the directory page itself)."""
    industry = infer_industry(target_roles)
    where = ", ".join(part for part in (city, country) if part)
    query = f"{industry} companies based in {where}" if where else f"{industry} companies"

    results = tavily_search(query, max_results=8)
    if not results:
        return []

    combined_text = "\n\n".join(
        f"{r.get('title', '')}\n{r.get('url', '')}\n{(r.get('content') or '')[:1500]}"
        for r in results
    )
    names = extract_company_names(combined_text)[:limit]

    companies = []
    for name in names:
        lookup_query = f"{name} official website"
        try:
            lookup_results = tavily_search(lookup_query, max_results=10)
        except Exception:
            continue
        candidates = [
            r["url"] for r in lookup_results if r.get("url") and not _is_denylisted(r["url"])
        ]
        if not candidates:
            continue
        # Prefer a candidate whose domain actually resembles the company name (its real
        # site) over whichever non-denylisted result simply ranked first - directories we
        # haven't explicitly denylisted often still outrank the real site.
        homepage_url = next(
            (url for url in candidates if _looks_like_companys_own_domain(name, url)),
            candidates[0],
        )
        # Search often ranks a deep page (terms of service, an about page, a blog post)
        # first; start from the site root so the scraper can find the real careers link.
        parts = urlparse(homepage_url)
        companies.append({"name": name, "homepage_url": f"{parts.scheme}://{parts.netloc}/"})

    return companies
