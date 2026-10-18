"""Spec 5.1: fetch new pages (and refresh old ones) into the dataset. One request per second per host."""
import asyncio
import hashlib
import json
import re
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from . import db
from .config import ROOT, Domain, Host, env

RAW = ROOT / "data/raw"


def parse_robots(text: str) -> list[tuple[bool, str]]:
    """Rules of every group addressed to '*' (our agent has no named group)."""
    rules, agents, in_rules = [], [], False
    for line in text.splitlines():
        key, _, value = line.split("#")[0].partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            agents = [] if in_rules else agents
            agents.append(value)
            in_rules = False
        elif key in ("allow", "disallow"):
            in_rules = True
            if "*" in agents and value:
                rules.append((key == "allow", value))
    return rules


def _pattern(rule: str) -> re.Pattern:
    return re.compile(re.escape(rule).replace(r"\*", ".*").removesuffix(r"\$") + ("$" if rule.endswith("$") else ""))


def robots_allows(rules: list[tuple[bool, str]], path: str) -> bool:
    """RFC 9309: the longest matching rule wins; on a tie, allow wins. `urllib.robotparser` ignores wildcards (D-07)."""
    hits = [(len(rule), allow) for allow, rule in rules if _pattern(rule).match(path)]
    return max(hits)[1] if hits else True


def normalise_url(url: str) -> str:
    u = urlsplit(url)
    return urlunsplit(("https", u.netloc.lower(), u.path or "/", "", ""))


def host_name(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def keep_link(host: str, url: str) -> bool:
    """A page on the same host: a path ending in .html or /, or a last segment without a file extension (TYPO3, Drupal)."""
    u = urlsplit(url)
    return u.scheme in ("http", "https") and host_name(url) == host and (
        u.path.endswith((".html", "/")) or "." not in u.path.rsplit("/", 1)[-1])


def raw_path(host: str, url: str) -> Path:
    return RAW / host / f"{hashlib.sha1(url.encode()).hexdigest()}.html"


def links(url: str, html: str, host: str) -> list[str]:
    hrefs = (a["href"] for a in BeautifulSoup(html, "lxml").find_all("a", href=True))
    return [normalise_url(u) for u in (urljoin(url, h) for h in hrefs) if keep_link(host, u)]


class HostFetcher:
    def __init__(self, conn, client: httpx.AsyncClient, host: Host, cap: int, refresh: bool):
        self.conn, self.client, self.host, self.cap, self.refresh = conn, client, host, cap, refresh
        self.name, self.last, self.count, self.started = host.name, 0.0, 0, time.time()
        self.rows = {r["url"]: r for r in conn.execute("SELECT * FROM dataset.pages WHERE host = %s", (self.name,))}

    async def get(self, url: str, headers: dict | None = None) -> httpx.Response:
        await asyncio.sleep(max(0.0, self.last + 1.0 - time.time()))
        self.last = time.time()
        return await self.client.get(url, headers=headers or {})

    def due(self, url: str) -> bool:
        row = self.rows.get(url)
        if row is None or row["status"] >= 500 or row["status"] == 429:   # server errors are retried on the next run
            return True
        stale = row["last_checked_at"] < datetime.now(timezone.utc) - timedelta(days=int(env("REFRESH_DAYS")))
        return self.refresh and row["gone_at"] is None and stale

    def store(self, url: str, status: int, body: bytes, headers: httpx.Headers | dict, modified: str | None = None):
        now = datetime.now(timezone.utc)
        path = raw_path(self.name, url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        row = self.conn.execute(
            """INSERT INTO dataset.pages VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL)
               ON CONFLICT (url) DO UPDATE SET status = EXCLUDED.status, last_checked_at = EXCLUDED.last_checked_at,
                 etag = EXCLUDED.etag, last_modified = EXCLUDED.last_modified, content_hash = EXCLUDED.content_hash
               RETURNING *""",
            (url, self.name, status, now, now, headers.get("etag"), modified or headers.get("last-modified"),
             hashlib.sha256(body).hexdigest(), str(path.relative_to(ROOT)))).fetchone()
        self.conn.commit()
        self.rows[url] = row
        self.count += 1
        if status != 200:
            print(f"{url}: HTTP {status}", flush=True)
        if self.count % 50 == 0:
            print(f"{self.name}: {self.count} pages, {self.count / (time.time() - self.started) * 3600:.0f} pages/hour", flush=True)

    def mark(self, url: str, gone: bool):
        self.conn.execute("UPDATE dataset.pages SET last_checked_at = now(), gone_at = CASE WHEN %s THEN now() END WHERE url = %s",
                          (gone, url))
        self.conn.commit()

    async def fetch_page(self, url: str) -> str | None:
        """Fetch or re-check one HTML page; returns its HTML when the page is (still) on this host."""
        row = self.rows.get(url)
        cond = {k: v for k, v in (("If-None-Match", row and row["etag"]), ("If-Modified-Since", row and row["last_modified"])) if v}
        r = await self.get(url, cond)
        if r.status_code == 304:
            self.mark(url, gone=False)
            return raw_path(self.name, url).read_text()
        if r.status_code in (404, 410) and row:
            self.mark(url, gone=True)
            return None
        final = normalise_url(str(r.url))
        if host_name(final) != self.name or (final != url and final in self.rows and not self.due(final)):
            return None
        self.store(final, r.status_code, r.content, r.headers)
        return r.text if r.status_code == 200 else None

    async def crawl(self, robots: list[tuple[bool, str]], seed_paths: list[str]):
        seeds = [normalise_url(urljoin(self.host.url, p)) for p in seed_paths]
        assert all(self.host.allows(urlsplit(u).path) for u in seeds), f"{self.name}: a seed is outside allow_paths"
        queue, seen = deque(seeds), set(seeds)
        while queue and len([r for r in self.rows.values() if r["status"] == 200]) < self.cap:
            url = queue.popleft()
            path = urlsplit(url).path
            if not robots_allows(robots, path) or not self.host.allows(path):
                continue
            html = await self.fetch_page(url) if self.due(url) else (
                raw_path(self.name, url).read_text() if self.rows[url]["status"] == 200 else None)
            leaf = any(re.search(rx, path) for rx in self.host.leaf_paths)
            for link in links(url, html, self.name) if html and not leaf else []:
                if link not in seen:
                    seen.add(link)
                    queue.append(link)

    async def wordpress(self, api: str, types: list[str]):
        """DCB: every post of the listed types through the WordPress REST API (decision D-11)."""
        for t in types:
            page, pages = 1, 1
            while page <= pages:
                r = await self.get(urljoin(self.host.url, f"{api}{t}?per_page=20&page={page}&_fields=link,type,modified,title,content"))
                assert r.status_code == 200, f"{r.url}: HTTP {r.status_code}"
                pages = int(r.headers["x-wp-totalpages"])
                for item in r.json():
                    url = normalise_url(item["link"])
                    known = self.rows.get(url)
                    if known is None or (self.refresh and known["last_modified"] != item["modified"]):
                        self.store(url, 200, json.dumps(item).encode(), {}, modified=item["modified"])
                page += 1


async def run(domain: Domain, refresh: bool, only: list[str] | None):
    hosts = sorted((h for h in domain.hosts if not only or h.name in only), key=lambda h: h.priority)
    assert hosts, f"no host matches {only}"
    headers = {"User-Agent": env("FETCH_USER_AGENT")}
    with db.connect() as conn:
        async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
            async def one(h: Host):
                f = HostFetcher(conn, client, h, domain.max_pages_per_host, refresh)
                t = domain.templates[h.template]
                if t.wp_api:
                    await f.wordpress(t.wp_api, t.wp_types)
                else:
                    r = await f.get(urljoin(h.url, "/robots.txt"))
                    assert r.status_code in (200, 404), f"{h.name} robots.txt: HTTP {r.status_code}"
                    await f.crawl(parse_robots(r.text) if r.status_code == 200 else [], h.seeds or t.seeds)
                print(f"{h.name}: done, {f.count} pages written this run", flush=True)

            results = await asyncio.gather(*(one(h) for h in hosts), return_exceptions=True)
    failed = [(h.name, repr(e)) for h, e in zip(hosts, results) if e is not None]
    assert not failed, f"hosts failed (rerun resumes): {failed}"
