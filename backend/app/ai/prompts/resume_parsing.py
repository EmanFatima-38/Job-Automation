RESUME_PARSING_SYSTEM_PROMPT = """\
You turn raw resume text into a structured profile.

Extract:
- projects: explicitly described projects, each with name, description, technologies
- portfolio_urls and github_url: only URLs actually present
- preferences: explicit role, seniority, employment or location preferences, otherwise {}
- portfolio_evidence: leave empty (website ingestion is performed separately)
- summary: a 1-2 sentence professional summary (write one if the resume doesn't have an explicit summary)
- skills: a flat list of skills, technologies, and tools mentioned anywhere in the resume
- experience: each job with title, company, start_date, end_date (use "Present" if current), and bullets (the responsibility/achievement lines)
- education: each degree with school and year
- city: the city the candidate is currently based in, if mentioned anywhere (null if not stated)
- country: the country the candidate is currently based in, if mentioned anywhere (null if not stated)
- target_roles: 3-5 job titles this candidate should search for, ordered from most to least relevant. Start with their actual/most recent title, then add closely related and adjacent roles their skills also qualify them for (e.g. an AI/ML engineer's skills usually also fit "Backend Developer", "Full Stack Developer", or "Software Engineer" - include roles like that when the skills support it). Keep titles short and generic (e.g. "Backend Developer", not "Backend Developer at Acme Corp").

Only extract what is actually present in the text. Do not invent companies, dates, or skills that aren't there. city, country, and target_roles may require light inference from context (e.g. a title or skillset implies a role family), but stay grounded in what's actually in the resume - do not fabricate unrelated roles.\
"""
