"""D-32: at search time each quoted source page is fetched again and the quote looked up in the page as it is now.

Plain HTTP, no browser: pages of hosts marked `render: browser` are not checked. Pages of one host are fetched one after
another, hosts in parallel; these pages are all in the dataset, so robots.txt allowed them."""
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from .config import Domain, env
from .models import Lead
from .normalise import clean_text, match_key
from .fetch import host_name

TIMEOUT = 5   # seconds per page; a slower page is reported unreachable


def key(text: str) -> str:
    """Letters and digits only: inline markup on the live page must not hide a quote."""
    return " ".join(re.sub(r"\W+", " ", match_key(clean_text(text))).split())


def status(client: httpx.Client, url: str, quotes: list[str]) -> dict[str, str]:
    """Quote -> found | changed (the page no longer has it) | gone (404, 410) | unreachable (timeout, other status)."""
    try:
        r = client.get(url)
    except httpx.HTTPError:
        return dict.fromkeys(quotes, "unreachable")
    if r.status_code in (404, 410):
        return dict.fromkeys(quotes, "gone")
    if r.status_code != 200:
        return dict.fromkeys(quotes, "unreachable")
    page = key(BeautifulSoup(r.text, "lxml").get_text(" "))
    return {q: "found" if key(q) in page else "changed" for q in quotes}


def check(domain: Domain, leads: list[Lead], progress=lambda event: None):
    """Sets `live` on every reason and `checked_at` on every lead; one progress event per page."""
    by_host: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for lead in leads:
        for r in lead.reasons:
            by_host[host_name(r.url)][r.url].append(r.sentence)
    result: dict[tuple[str, str], str] = {}

    def host(name: str):
        rendered = domain.host(name).render is not None
        with httpx.Client(headers={"User-Agent": env("FETCH_USER_AGENT")}, timeout=TIMEOUT, follow_redirects=True) as client:
            for url, quotes in by_host[name].items():
                s = dict.fromkeys(quotes, "not_checked") if rendered else status(client, url, quotes)
                result.update({(url, q): v for q, v in s.items()})
                progress({"step": "verify", "url": url, "found": sum(v == "found" for v in s.values()), "quotes": len(s),
                          "status": sorted(set(s.values()))})

    with ThreadPoolExecutor(max(len(by_host), 1)) as ex:
        list(ex.map(host, by_host))
    now = datetime.now(timezone.utc)
    for lead in leads:
        lead.checked_at = now
        for r in lead.reasons:
            r.live = result[(r.url, r.sentence)]
