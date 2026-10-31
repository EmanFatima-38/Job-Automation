"""Conservative page evidence. Unknown is distinct from a confirmed non-vacancy."""
import re
from urllib.parse import urlsplit, urljoin
from lxml import html as lxml_html


def page_kind(url: str) -> str:
    p = urlsplit(url)
    host, path = (p.hostname or '').lower(), p.path.lower().rstrip('/')
    if any(host == d or host.endswith('.' + d) for d in ('facebook.com', 'instagram.com', 'youtube.com', 'tiktok.com', 'threads.com', 'twitter.com', 'x.com')):
        return 'irrelevant'
    if re.search(r'/(blog|blogs|courses?|training|news)/|salary-in-|course-', path):
        return 'irrelevant'
    if '/jsearch/' in path:
        return 'directory'
    if ('indeed.' in host and re.search(r'/q-|/jobs$', path)) or '/jobs/search' in path:
        return 'directory'
    if 'linkedin.com' in host and '/jobs/' in path and '/view/' not in path:
        return 'directory'
    if 'glassdoor.' in host and 'srch_' in path:
        return 'directory'
    if 'remoterocketship.com' in host and ('/country/' in path or path.endswith('/internships')):
        return 'directory'
    if re.search(r'-jobs-in-|-jobs$|/remote-[^/]*-jobs', path):
        return 'directory'
    if path in ('/jobs', '/careers', '/students', '/v2/global/en/students'):
        return 'directory'
    return 'candidate'


def clean_page(html: str) -> str:
    try:
        tree = lxml_html.fromstring(html)
        for node in tree.xpath('//script[not(@type="application/ld+json")] | //style | //nav | //footer | //form | //noscript'):
            node.drop_tree()
        return lxml_html.tostring(tree, encoding='unicode')
    except (ValueError, TypeError):
        return html


def is_training_program(text: str) -> bool:
    """A paid-training/bootcamp enrollment page, not an employer's job posting. Genuine
    job postings can mention 'training' or even 'certificate' in passing, so require the
    stronger, more specific signals a course/cohort page actually uses rather than any
    single keyword."""
    t = (text or '').lower()
    strong = re.search(r'\bcohort\s*\d+\b|\benroll now\b|\bapply for cohort\b|\benrol+ment\b', t)
    modules = len(re.findall(r'\bmodule\s*0?\d\b', t)) >= 2
    return bool(strong or modules)


def specific_vacancy(text: str, title: str | None, company: str | None) -> bool:
    """Conflicting model classification requires review, never automatic acceptance."""
    return bool(title and company and company.lower() in text.lower()
                and re.search(r'(?i)responsibilities|what you.ll do|about the role', text)
                and re.search(r'(?i)requirements|what we.re looking for|qualifications', text))


def application_link(html: str, base: str) -> str | None:
    try:
        tree = lxml_html.fromstring(html)
        for a in tree.xpath('//a[@href]'):
            label = ' '.join([a.text_content(), a.get('aria-label', '')]).strip()
            if re.search(r'(?i)how to|guide|tips|help|advice', label):
                continue
            if not re.search(r'(?i)\bapply(?: now| for (?:this|the) (?:job|role|position))?\b', label):
                continue
            href = a.get('href', '').strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:')):
                continue
            target = urljoin(base, href)
            p = urlsplit(target)
            if p.scheme in ('http', 'https') and p.hostname and not p.username and not p.password and p.port in (None, 80, 443):
                return target
        for form in tree.xpath('//form[.//input[@type="file"]]'):
            if re.search(r'(?i)\b(cv|resume|cover letter)\b', form.text_content()) and re.search(r'(?i)apply|application|submit', form.text_content()):
                return base  # The fetched page hosts the application form; do not submit it.
    except (ValueError, TypeError):
        pass
    return None
