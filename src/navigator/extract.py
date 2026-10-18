"""Spec 5.2 and 5.3: main text, page types, cleaning, units, people, projects and facilities."""
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .config import LANGS, ROOT, Domain, Template, load_yaml
from .fetch import normalise_url
from .normalise import AI_ADDRESSED, clean_text, words

BLOCKS = ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "dt", "dd", "div", "section", "article",
          "aside", "tr", "address", "blockquote", "figcaption", "br"]
LANG_SUFFIX = {"_eng": "en", "_ger": "de", "_fra": "fr"}
TITLES = {"prof.", "em.", "dr.", "pd", "med.", "phil.", "nat.", "rer.", "dent.", "vet.", "sc.", "techn.", "habil.",
          "pharm.", "jur.", "oec.", "hist.", "dipl.", "ing.", "msc", "phd", "md", "mba", "bsc", "dr", "prof"}
MIN_WORDS = 30  # a page with less content carries no evidence


@dataclass
class Page:
    url: str
    host: str
    lang: str
    page_type: str
    title: str
    page_date: str | None
    text: str
    text_hash: str
    unit_id: str = ""
    translation_of: str | None = None
    lang_links: list[str] = field(default_factory=list)
    people: list[tuple[str, str]] = field(default_factory=list)   # (name as written, role) from member lists


@dataclass
class Unit:
    id: str
    name: str
    kind: str
    parent_id: str | None
    host: str


def host_short(host: str) -> str:
    return host.split(".")[0]


def split_name(written: str) -> tuple[str, str]:
    """'Prof. Dr. Muster, Hans' or 'Prof. Dr. Hans Muster' -> ('Hans Muster', 'Prof. Dr.')."""
    tokens = written.replace(",", " , ").split()
    titles = [t for t in tokens if t.lower() in TITLES]
    rest = " ".join(t for t in tokens if t.lower() not in TITLES)
    surname, comma, first = rest.partition(" , ")
    name = f"{first.strip(' ,')} {surname.strip(' ,')}" if comma else rest.strip(" ,")
    return " ".join(name.split()), " ".join(titles)


def page_type(template: Template, key: str) -> str:
    return next(t for t, rx in template.page_types.items() if re.search(rx, key))


def block_text(el) -> str:
    for tag in el.find_all(BLOCKS):
        tag.insert_after("\n")
    return el.get_text()


def cut_alumni(text: str, headings: list[str]) -> str:
    lines = text.splitlines()
    cut = next((i for i, line in enumerate(lines) if line.strip() in headings), len(lines))
    return "\n".join(lines[:cut])


def member_rows(text: str) -> list[tuple[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    names = [i + 1 for i, line in enumerate(lines[:-1]) if line in ("Name / Titel", "Name / Title")]
    role = lambda i: next((lines[j + 1] for j in range(i, min(i + 4, len(lines) - 1)) if lines[j] in ("Funktion", "Function")), "")
    return [(lines[i], role(i)) for i in names]


def parse_html(domain: Domain, host: str, url: str, html: str) -> Page | None:
    t = domain.templates[domain.host(host).template]
    soup = BeautifulSoup(html, "lxml")
    if t.skip_without and not soup.select(t.skip_without):
        print(f"no content area (navigation page): {url}")
        return None
    mains = soup.select(t.main)
    assert len(mains) == 1, f"{url}: {len(mains)} matches for {t.main!r}; fix the template"
    main = mains[0]
    for sel in [*t.drop, "script", "style", "noscript", "form"]:
        for el in main.select(sel):
            el.decompose()
    raw = cut_alumni(block_text(main), t.alumni_headings)
    path = urlsplit(url).path
    (lang,) = [v for k, v in LANG_SUFFIX.items() if path.endswith(f"index{k}.html")] or [
        {"eng": "en", "ger": "de", "fra": "fr"}[soup.find("meta", attrs={"name": "DC.Language"})["content"]]]
    date = soup.find("meta", attrs={"name": "DC.Date"})
    h1 = main.find("h1")
    title = clean_text(h1.get_text(" ") if h1 else soup.find("meta", attrs={"name": "DC.Title"})["content"])
    switch = [normalise_url(a["href"]) for a in soup.find_all("a", href=True) if a.get_text(strip=True) in ("DE", "EN", "FR")]
    text = clean_text(raw)
    ptype = page_type(t, path)
    return Page(url, host, lang, ptype, title, date and datetime.strptime(date["content"], "%d.%m.%Y").date().isoformat(),
                text, hashlib.sha256(text.encode()).hexdigest(), lang_links=[u for u in switch if u != url],
                people=member_rows(raw) if ptype == "members" else [])


def parse_wordpress(domain: Domain, host: str, url: str, item: dict) -> Page:
    t = domain.templates[domain.host(host).template]
    text = block_text(BeautifulSoup(item["content"]["rendered"], "lxml"))
    text = clean_text(re.sub("|".join(t.strip_patterns) or "$^", "", text))
    title = clean_text(BeautifulSoup(item["title"]["rendered"], "lxml").get_text(" "))
    (lang,) = [seg for seg in urlsplit(url).path.split("/")[1:2] if seg in LANGS]
    return Page(url, host, lang, page_type(t, item["type"]), title, item["modified"][:10], text,
                hashlib.sha256(text.encode()).hexdigest())


def assign_units(domain: Domain, pages: list[Page]) -> list[Unit]:
    """A unit is a host (its institute or centre) or a path matching the unit_paths that has its own index page.
    Every page belongs to the deepest unit above it; a translated index page joins its English unit."""
    units = {host_short(h.name): Unit(host_short(h.name), h.label, "institute", None, h.name) for h in domain.hosts}
    codes, index_of = {}, {}
    for p in pages:
        h = domain.host(p.host)
        rxs = h.unit_paths if h.unit_paths is not None else domain.templates[h.template].unit_paths
        m = next((m for rx in rxs if (m := re.match(rx, urlsplit(p.url).path))), None)
        codes[p.url] = m and f"{host_short(p.host)}-{m.group(1).replace('_', '-')}"
        if m and urlsplit(p.url).path[m.end():] in ("index_eng.html", "index_ger.html", "index_fra.html", ""):
            index_of[p.url] = codes[p.url]
    same = {index_of[p.url]: twin for p in pages if p.url in index_of and p.lang != "en"
            for twin in [next((index_of[u] for u in p.lang_links if index_of.get(u, index_of[p.url]) != index_of[p.url]), None)] if twin}
    homes = {h.url + rest for h in domain.hosts for rest in ("", "index_eng.html", "index_ger.html", "index_fra.html", "en/", "de/", "fr/")}
    for p in pages:
        if p.url in homes:
            p.page_type = "group"                            # a host's home page is its unit's index page
    for p in sorted(pages, key=lambda p: p.lang != "en"):   # an English index page names the unit when there is one
        if p.url in index_of:
            uid = same.get(index_of[p.url], index_of[p.url])
            units.setdefault(uid, Unit(uid, p.title, "group", host_short(p.host), p.host))
            p.page_type = "group"
    for p in pages:
        uid = same.get(codes[p.url], codes[p.url])
        p.unit_id = uid if uid in units else host_short(p.host)
    used = {p.unit_id for p in pages}
    return [u for u in units.values() if u.id in used]


def apply_aliases(units: list[Unit], pages: list[Page]) -> list[Unit]:
    aliases = {other: canon for canon, others in load_yaml("aliases.yaml").items() for other in others}
    ids = {u.id for u in units}
    assert all(a in ids and c in ids for a, c in aliases.items()), f"alias to a missing unit: {aliases}"
    for p in pages:
        p.unit_id = aliases.get(p.unit_id, p.unit_id)
    return [u for u in units if u.id not in aliases]


def dedupe(domain: Domain, pages: list[Page]) -> list[Page]:
    rank = {h.name: h.priority for h in domain.hosts}
    kept: dict[str, Page] = {}
    for p in sorted(pages, key=lambda p: (rank[p.host], p.url)):
        if p.text_hash in kept:
            print(f"duplicate: {p.url} = {kept[p.text_hash].url}")
        else:
            kept[p.text_hash] = p
    return list(kept.values())


def flagged_check(pages: list[Page]) -> list[Page]:
    """Pages addressed to an AI system stop the build until excluded or cleared (spec section 4)."""
    cfg = load_yaml("flagged_pages.yaml")
    hits = {p.url for p in pages if AI_ADDRESSED.search(p.text)}
    open_ = hits - set(cfg["excluded"]) - set(cfg["cleared"])
    assert not open_, f"pages addressed to an AI system; exclude or clear in config/flagged_pages.yaml: {sorted(open_)}"
    return [p for p in pages if p.url not in cfg["excluded"]]


def load_pages(conn, domain: Domain) -> list[Page]:
    hosts = {h.name: domain.templates[h.template] for h in domain.hosts}
    rows = conn.execute("SELECT url, host, raw_path FROM dataset.pages WHERE status = 200 AND gone_at IS NULL "
                        "AND host = ANY(%s) ORDER BY url", (list(hosts),)).fetchall()
    assert rows, "dataset is empty; run navigator fetch"
    raw = lambda r: (ROOT / r["raw_path"]).read_text(encoding="utf-8")
    pages = [parse_wordpress(domain, r["host"], r["url"], json.loads(raw(r))) if hosts[r["host"]].wp_api
             else parse_html(domain, r["host"], r["url"], raw(r)) for r in rows]
    return [p for p in pages if p]


def run(conn, domain: Domain) -> dict:
    pages = flagged_check(dedupe(domain, [p for p in load_pages(conn, domain) if words(p.text) >= MIN_WORDS]))
    units = apply_aliases(assign_units(domain, pages), pages)
    urls = {p.url for p in pages}
    for p in pages:
        p.translation_of = next((u for u in p.lang_links if u in urls), None) if p.lang != "en" else None
    people = [dict(unit_id=p.unit_id, first_last=n, titles=t, role=role, url=p.url)
              for p in pages for written, role in p.people for n, t in [split_name(written)] if n]
    for p in pages:   # the source page lists titles in the name field (D-20)
        for written, _ in p.people:
            if not split_name(written)[0]:
                print(f"member row without a name, left out: {written!r} on {p.url}")
    items = [dict(unit_id=p.unit_id, kind=p.page_type, name=p.title, url=p.url)
             for p in pages if p.page_type in ("project", "facility")]
    out = {"pages": [asdict(p) for p in pages], "units": [asdict(u) for u in units], "people": people, "items": items}
    assert len({u.id for u in units}) == len(units), "unit ids are not unique"
    assert {p.unit_id for p in pages} <= {u.id for u in units}
    print(f"extract: {len(pages)} pages, {len(units)} units, {len(people)} people, {len(items)} items")
    return out
