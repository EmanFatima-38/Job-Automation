"""Bounded public HTTP retrieval shared by user URLs and discovery enrichment."""
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

MAX_BYTES = 2_000_000
AGENT = 'ApplyPilotBot'


def validate_public_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Only public HTTP(S) URLs without credentials are allowed')
    if parsed.port not in (None, 80, 443):
        raise ValueError('Only standard web ports are allowed')
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError('Cannot resolve website') from exc
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Private, local and reserved network addresses are blocked')
    return url


_META_CHARSET = re.compile(rb"""<meta[^>]+charset=["']?([\w-]+)""", re.I)


def decode_body(body: bytes, content_type: str = '') -> str:
    """Decode with the declared charset (header, then <meta>), not a blanket UTF-8
    assumption that turns Latin-1/Windows-1252 pages into replacement characters."""
    declared = re.search(r"""charset=["']?([\w-]+)""", content_type or '', re.I)
    meta = _META_CHARSET.search(body[:4096])
    for charset in (declared and declared.group(1), meta and meta.group(1).decode('ascii', 'ignore')):
        if charset:
            try:
                return body.decode(charset)
            except (LookupError, UnicodeDecodeError):
                continue
    try:
        return body.decode('utf-8')
    except UnicodeDecodeError:
        return body.decode('cp1252', errors='replace')


def _download(url: str) -> tuple[str, str]:
    # Validate each redirect; disable environment proxies for these untrusted URLs.
    with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
        for _ in range(5):
            validate_public_url(url)
            with client.stream('GET', url, headers={'User-Agent': AGENT + '/1.0'}) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get('location', ''))
                    continue
                response.raise_for_status()
                content_type = response.headers.get('content-type', '').lower()
                if content_type and not any(t in content_type for t in ('text/', 'json', 'xml', 'xhtml')):
                    raise ValueError('Unsupported website content type')
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError('Website response exceeds 2 MB')
                    chunks.append(chunk)
                return decode_body(b''.join(chunks), content_type), url
    raise ValueError('Too many website redirects')


def fetch_public_page(url: str, respect_robots: bool = True) -> tuple[str, str]:
    validate_public_url(url)
    if respect_robots:
        p = urlsplit(url)
        robots_url = f'{p.scheme}://{p.netloc}/robots.txt'
        try:
            robots, _ = _download(robots_url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in (404, 410):
                raise ValueError('Website access policy could not be checked') from exc
        else:
            parser = RobotFileParser()
            parser.parse(robots.splitlines())
            if not parser.can_fetch(AGENT, url):
                raise ValueError('Website disallows automated access')
    return _download(url)
