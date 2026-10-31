"""Public-network and robots policy for browser-based discovery."""
import threading
from contextlib import contextmanager
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import httpx
from app.services.safe_fetch import validate_public_url, _download, AGENT

_local = threading.local()


class RenderBudgetExhausted(Exception):
    """The caller's allowance of slow browser renders is used up; retry in a later pass."""


@contextmanager
def browser_session(max_renders: int | None = None):
    """Share one launched browser across this thread's renders (launching Chromium per
    page dominated render time) and optionally cap how many renders may run. Pages still
    get a fresh, isolated browser context each."""
    state = {'browser': None, 'playwright': None, 'remaining': max_renders}
    previous = getattr(_local, 'session', None)
    _local.session = state
    try:
        yield state
    finally:
        _local.session = previous
        try:
            if state['browser'] is not None:
                state['browser'].close()
        finally:
            if state['playwright'] is not None:
                state['playwright'].stop()


def _render(browser, url, timeout_ms, settle_ms):
    context = browser.new_context(user_agent=AGENT + '/1.0')
    try:
        page = context.new_page()
        protect_page(page)
        page.goto(url, timeout=timeout_ms, wait_until='domcontentloaded')
        page.wait_for_timeout(settle_ms)
        return page.content(), page.url
    finally:
        context.close()


def fetch_rendered_page(url: str, timeout_ms: int = 20000, settle_ms: int = 2500) -> tuple[str, str]:
    """Render a page with a real browser under the same public-network/robots policy as
    the plain HTTP fetch. Used as a fallback when a static GET comes back suspiciously
    short - the signature of a JS-rendered single-page app or a bot-protection challenge
    shell (e.g. Cloudflare) that a plain client can never get past. This is common on
    Workable/Greenhouse/Lever-style ATS platforms this app specifically needs to read, so
    treating a blocked static fetch as proof the page itself is unreachable was wrong."""
    from playwright.sync_api import sync_playwright
    validate_public_url(url)
    session = getattr(_local, 'session', None)
    if session is None:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                return _render(browser, url, timeout_ms, settle_ms)
            finally:
                browser.close()
    if session['remaining'] is not None:
        if session['remaining'] <= 0:
            raise RenderBudgetExhausted('Browser render budget for this pass is used up')
        session['remaining'] -= 1
    if session['browser'] is None:
        session['playwright'] = sync_playwright().start()
        session['browser'] = session['playwright'].chromium.launch()
    return _render(session['browser'], url, timeout_ms, settle_ms)


def protect_page(page):
    policies = {}
    public_hosts = set()
    def guard(route):
        url = route.request.url
        try:
            parsed = urlsplit(url)
            host = (parsed.scheme, parsed.netloc)
            # Validate every document request (including redirects); cache subresources.
            if route.request.is_navigation_request() or host not in public_hosts:
                validate_public_url(url)
                public_hosts.add(host)
            if route.request.resource_type in ('image', 'media', 'font'):
                route.abort()
                return
            if route.request.is_navigation_request():
                if host not in policies:
                    robot = RobotFileParser()
                    try:
                        text, _ = _download(f'{parsed.scheme}://{parsed.netloc}/robots.txt')
                        robot.parse(text.splitlines())
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code not in (404, 410):
                            raise ValueError('Cannot verify browser access policy') from exc
                        robot.parse([])
                    policies[host] = robot
                if not policies[host].can_fetch(AGENT, url):
                    raise ValueError('Automated browser access disallowed')
            route.continue_()
        except Exception:
            route.abort()
    page.route('**/*', guard)
