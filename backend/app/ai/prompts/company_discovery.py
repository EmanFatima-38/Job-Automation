INDUSTRY_LABEL_SYSTEM_PROMPT = """\
You turn a candidate's target job titles into a short industry/sector label suitable for \
searching "<label> companies based in <city>".

Examples:
- "AI Engineer, Backend Developer, Full Stack Developer" -> "software development"
- "Corporate Lawyer, Litigation Associate" -> "law"
- "Registered Nurse, ICU Nurse" -> "healthcare"
- "Accountant, Financial Analyst" -> "accounting and finance"

Keep it to 1-4 words, lowercase, no punctuation. Pick the single best general label that \
covers the roles given.\
"""

COMPANY_NAME_EXTRACTION_SYSTEM_PROMPT = """\
You read raw web search results (titles, URLs, and content snippets) about companies in a \
specific industry and city, and extract a clean, deduplicated list of real, individual \
company names mentioned anywhere in the text.

Rules:
- Only include names that are unambiguously the proper name of a real employer company, \
firm, or organization - the kind of thing that would appear on someone's resume as "worked \
at X" or that has its own dedicated careers page.
- Exclude: job boards, recruitment agencies, directory/listicle sites, news articles, \
Wikipedia-style definitions, generic terms, conferences/events/summits, associations, \
and the name of the directory site itself.
- A name must be clearly presented AS a company in the text (e.g. "X is a software company \
based in...", "X Technologies", "X Solutions"). If a word or phrase is just part of a \
sentence describing something else (a topic, a program name, a scenario, an event title) \
and not actually introduced as a company, do not include it - when genuinely unsure, leave \
it out rather than guess.
- Do not invent companies that aren't mentioned in the text.
- Return each company name once, in the form it's most clearly/commonly referred to in the text.\
"""

COMPANY_JOB_EXTRACTION_SYSTEM_PROMPT = """\
You are given the rendered text content of a company's careers/jobs page, plus a list of \
links (text and href) found on that page. Identify genuine open job postings.

For each posting, give:
- title: the job title as written
- url: the href from the links list that best matches this posting, if you can confidently \
match one. Use null if no link clearly corresponds to this specific posting (e.g. the page \
only lists titles with no per-job links, or the only links are generic "Apply" buttons \
with no distinguishing href).

Ignore navigation links, "About us", benefits sections, cookie/privacy links, login/signup \
links, and anything that is not an actual job title. A genuine posting is a role someone \
could be HIRED for at this company - explicitly exclude conferences, summits, webinars, \
trade shows, events, and training programs, even if the page frames them as opportunities; \
those are not jobs. If the page has no genuine open positions, return an empty list - do \
not invent postings.\
"""
