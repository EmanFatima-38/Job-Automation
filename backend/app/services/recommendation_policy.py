"""One evidence gate for the dashboard and opportunity delivery; no model-only approval."""
import re
from datetime import datetime, timezone, timedelta

# Bump to force every stored posting through enrichment and rescoring again.
POLICY_VERSION = 3
COUNTRIES = {
    'pakistan': ('pakistan', 'pk'), 'united states': ('united states', 'usa', 'us', 'u.s.', 'united states of america'),
    'united kingdom': ('united kingdom', 'uk', 'u.k.', 'great britain'),
    # Bare 'CA' is deliberately not treated as a Canada alias - in job postings it is far
    # more often the US state California (e.g. "CA residents only"); 'canada' spelled out
    # or 'CAN' is unambiguous and still matches.
    'canada': ('canada', 'can'), 'india': ('india', 'in'), 'germany': ('germany', 'de'),
    'australia': ('australia', 'au'), 'united arab emirates': ('united arab emirates', 'uae'),
}


def country_names(value):
    text = str(value or '').lower()
    # Bare short codes are accepted; in prose, require uppercase to avoid "in"/"us" pronouns.
    found = set()
    for country, aliases in COUNTRIES.items():
        for alias in aliases:
            if len(alias) <= 3 and alias.isalpha():
                hit = text.strip(' \"[]{}') == alias or re.search(r'(?<!\w)' + re.escape(alias.upper()) + r'(?!\w)', str(value))
            else:
                hit = re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text)
            if hit:
                found.add(country)
    return found


def remote_restriction(restriction, country):
    if not country:
        return None, 'Candidate remote eligibility country is not set'
    if not restriction:
        return None, 'Remote applicant country eligibility unknown'
    wanted, allowed = country_names(country), country_names(restriction)
    lower = str(restriction).lower()
    for name in wanted:
        if re.search(r'\b(?:except|excluding|not (?:in|from)|not eligible in)\s+' + re.escape(name), lower):
            return 'Candidate country is explicitly excluded', None
    if any(w in lower for w in ('worldwide', 'anywhere', 'global')) and not re.search(r'\b(except|excluding|not eligible)\b', lower):
        return None, None
    if re.search(r'\b(except|excluding|not eligible)\b', lower):
        return None, f'Confirm regional exceptions for {country}: {restriction}'
    if wanted and allowed and wanted.isdisjoint(allowed):
        return f'Remote country restriction: {restriction}', None
    if wanted and allowed == wanted and not re.search(r'\b(except|excluding|not eligible)\b', lower):
        return None, None
    if wanted and wanted.intersection(allowed) and not re.search(r'\b(except|excluding|not eligible)\b', lower):
        return None, None
    return None, f'Confirm eligibility for {country}: {restriction}'


_NUMBER_WORDS = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
    'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12,
    'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'twenty': 20,
}
_YEARS_PATTERN = re.compile(
    r'(?i)(\d+|' + '|'.join(_NUMBER_WORDS) + r')\s*(?:\+|[-–]\s*(?:\d+|' + '|'.join(_NUMBER_WORDS) + r'))?'
    r'\s*years?\s+(?:of\s+)?(?:professional\s+|relevant\s+|work\s+)?experience'
)


def _years_value(token):
    token = token.lower()
    return _NUMBER_WORDS.get(token, None) if not token.isdigit() else int(token)


def candidate_experience_years(profile):
    """Best-effort total career span (earliest start to latest end/'present') from the
    resume's own stated experience. Returns None when nothing parseable is present -
    callers must treat that as unknown, never as zero."""
    entries = (profile or {}).get('experience') or []
    starts, ends = [], []
    now_year = datetime.now(timezone.utc).year
    for entry in entries:
        entry = entry if isinstance(entry, dict) else {}
        start_match = re.search(r'(19|20)\d{2}', str(entry.get('start_date') or ''))
        if start_match:
            starts.append(int(start_match.group(0)))
        end_raw = str(entry.get('end_date') or '')
        end_match = re.search(r'(19|20)\d{2}', end_raw)
        if end_match:
            ends.append(int(end_match.group(0)))
        elif not entry.get('end_date') or re.search(r'(?i)present|current|ongoing|now', end_raw):
            ends.append(now_year)
    if not starts:
        return None
    return max(0, (max(ends) if ends else now_year) - min(starts))


def mandatory_evidence(job, profile=None):
    """Fail uncertain mandatory conditions closed. Never infer dates, enrollment or visas."""
    rejected, concerns = [], []
    requirements = getattr(job, 'requirements', None) or []
    # Keep raw clauses as a fallback for missing extracted requirements.
    clauses = requirements + re.split(r'[\n.;]', getattr(job, 'raw_input_text', '') or '')
    minima = []
    enrollment = authorization = False
    for clause in clauses:
        if re.search(r'(?i)preferred|desirable|nice.to.have|not required|no .* required'
                     r'|\bis an? (?:plus|bonus|advantage)\b|\badvantageous\b|\bideal(?:ly)?\b|\bnice if\b|\bbenefit\b', clause):
            continue
        years = _YEARS_PATTERN.search(clause)
        if years:
            value = _years_value(years.group(1))
            if value is not None:
                minima.append(value)
        enrollment |= bool(re.search(r'(?i)(currently (?:enrolled|studying)|must be (?:a )?student|enrollment required)', clause))
        authorization |= bool(re.search(r'(?i)(work authori[sz]ation|right to work|citizenship|security clearance|must be (?:a )?citizen)', clause))
    required_years = max(minima) if minima else 0
    if required_years > 0:
        # A posting that only ever mentions "0" or "0-N years" (e.g. "0-2 years, fresh
        # graduates welcome") isn't a minimum anyone could fail to meet.
        actual_years = candidate_experience_years(profile)
        if actual_years is None or actual_years < required_years:
            concerns.append(f'Confirm at least {required_years} years of relevant experience from CV evidence')
    if enrollment:
        evidence = ' '.join(str(e) for e in (profile or {}).get('education', []))
        if not re.search(r'(?i)currently enrolled|currently studying', evidence):
            concerns.append('Current student enrollment requires explicit confirmation')
    if authorization:
        concerns.append('Work authorization or citizenship requirement needs explicit confirmation')
    return rejected, concerns


def recommendation(job, user, resume, match, *, use_plan=True):
    from app.services.job_quality import eligibility, parse_date, current_plan
    from app.services.portfolio_service import candidate_profile
    from app.services.discovery_backlog import match_context
    prefs = {**(user.preferences or {})}
    prefs['max_age_days'] = prefs.get('max_age_days') or 30
    research = job.research or {}
    profile = candidate_profile(user, resume) if resume else {}
    rejected, concerns = eligibility(job, prefs, current_plan(job, user) if use_plan else None, profile)
    _, mandatory = mandatory_evidence(job, profile)
    concerns += mandatory
    now = datetime.now(timezone.utc)
    checked = parse_date(research.get('last_verified_at'))
    if research.get('state') != 'active':
        concerns.append('Opening is not confirmed active')
    if research.get('is_job_posting') is not True:
        concerns.append('Individual vacancy is not confirmed')
    if not job.company:
        concerns.append('Hiring company is unknown')
    if not checked or checked < now - timedelta(days=1) or checked > now + timedelta(minutes=5):
        concerns.append('Vacancy needs a current page check')
    if research.get('application_link_status') != 'reachable':
        concerns.append('Application destination has not been checked')
    if research.get('evidence_version') != POLICY_VERSION:
        concerns.append('Vacancy needs updated evidence checks')
    if not resume or resume.parse_status != 'parsed':
        concerns.append('A parsed primary CV is required')
    if not match or not resume or match.context_hash != match_context(user, resume, job):
        concerns.append('A current evidence-based match is required')
    else:
        concerns += (match.details or {}).get('eligibility_concerns', [])
        if match.match_score < 75:
            concerns.append('Estimated fit is below the recommendation threshold')
    rejected, concerns = list(dict.fromkeys(rejected)), list(dict.fromkeys(concerns))
    status = 'excluded' if rejected else 'needs_review' if concerns else 'recommended'
    return {'recommendation_status': status, 'recommendation_reasons': rejected + concerns,
            'exclusion_reasons': rejected, 'eligibility_concerns': concerns}
