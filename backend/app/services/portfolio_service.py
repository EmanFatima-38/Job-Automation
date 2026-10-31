from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.schemas.discovery import Preferences
from app.services.safe_fetch import fetch_public_page
from app.services.job_mapping import html_to_text


def refresh_portfolio(db, user):
    prefs = Preferences.model_validate(user.preferences or {})
    urls = list(dict.fromkeys(prefs.portfolio_urls + ([prefs.github_url] if prefs.github_url else [])))[:5]
    old = user.portfolio_data or {}
    result = {}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=get_settings().portfolio_refresh_hours)
    for url in urls:
        cached = old.get(url, {})
        if cached.get('refreshed_at') and datetime.fromisoformat(cached['refreshed_at']) > cutoff:
            result[url] = cached
            continue
        try:
            html, final_url = fetch_public_page(url)
            text = html_to_text(html)[:16000]
            result[url] = {'url': final_url, 'text': text, 'refreshed_at': datetime.now(timezone.utc).isoformat(), 'error': None}
        except Exception as exc:
            result[url] = {**cached, 'error': str(exc)[:300]}
    user.portfolio_data = result
    db.commit()
    return result


def candidate_profile(user, resume) -> dict:
    profile = dict(resume.structured_profile or {}) if resume else {}
    prefs = Preferences.model_validate(user.preferences or {})
    profile['projects'] = [*profile.get('projects', []), *prefs.projects]
    profile['preferences'] = prefs.model_dump()
    profile['portfolio_evidence'] = [entry['text'][:10000] for entry in (user.portfolio_data or {}).values() if entry.get('text')]
    return profile
