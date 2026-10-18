"""Spec 5.2 and 5.3: main text, page types, cleaning, units, people, projects and facilities."""
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .config import LANGS, ROOT, Domain, Template, load_yaml
from .fetch import normalise_url
from .normalise import AI_ADDRESSED, EMAIL, PHONE, clean_text, match_key, words

BLOCKS = ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "dt", "dd", "div", "section", "article",
          "aside", "tr", "address", "blockquote", "figcaption", "br"]
LANG_SUFFIX = {"_eng": "en", "_ger": "de", "_fra": "fr", "_ita": None}   # Italian pages are not indexed
LANG_META = {"eng": "en", "ger": "de", "fra": "fr", "ita": None}
TITLES = {"prof.", "em.", "dr.", "pd", "med.", "phil.", "nat.", "rer.", "dent.", "vet.", "sc.", "techn.", "habil.",
          "pharm.", "jur.", "oec.", "hist.", "dipl.", "ing.", "msc", "phd", "md", "mba", "bsc", "dr", "prof"}
MIN_WORDS = 30  # a page with less content carries no evidence
LEAD_ROLE = re.compile(r"head|director|leader|principal investigator|\bPI\b|leiter|direktor", re.I)   # contact person (D-26)


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
    people: list[dict] = field(default_factory=list)   # schema.org Person entries on the page (D-26)


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


def person_entries(main, url: str, t: Template) -> list[dict]:
    """The template's person cards: on a member list (with a link to the person's own page) or on the person's own
    page (`link` is None). Entries after an alumni heading are left out."""
    cut = next((h for h in main.find_all(["h1", "h2", "h3", "h4"]) if h.get_text(strip=True) in t.alumni_headings), None)
    after = {id(el) for el in cut.find_all_next()} if cut else set()
    text = lambda el: el and (" ".join(el.get_text(" ").split()) or None)
    found = lambda rx, el: (m := el and re.search(rx, f"{el.get_text(' ')} {el.get('href', '')}")) and m.group(0)   # text or mailto: link
    out = []
    for spec in t.people:
        for card in main.select(spec.card):
            if id(card) in after:
                continue
            sel = lambda css: css and card.select_one(css)
            a = sel(spec.link)
            link = url if spec.link is None else a and a.get("href") and normalise_url(urljoin(url, a["href"]))
            out.append(dict(name=text(sel(spec.name)) or "", function=text(sel(spec.function)), affiliation=text(sel(spec.affiliation)),
                            profile_url=link, email=found(EMAIL, sel(spec.email)), phone=found(PHONE, sel(spec.phone)),
                            own_page=spec.link is None))
    return out


def page_lang(t: Template, soup, path: str) -> str | None:
    """None for a language the index does not cover. UniBE: file suffix or DC.Language; other sites: a path segment."""
    if t.lang_segment is None:
        (lang,) = [v for k, v in LANG_SUFFIX.items() if path.endswith(f"index{k}.html")] or [
            LANG_META[soup.find("meta", attrs={"name": "DC.Language"})["content"]]]
        return lang
    seg = ([s for s in path.split("/") if s][t.lang_segment:t.lang_segment + 1] or [""])[0]
    return seg if seg in LANGS else None if re.fullmatch("[a-z]{2}", seg) else t.default_lang


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
    lang = page_lang(t, soup, path)
    if lang is None:
        print(f"language not indexed: {url}")
        return None
    date = soup.find("meta", attrs={"name": "DC.Date"})
    h1 = main.find("h1")
    meta_title = soup.find("meta", attrs={"name": "DC.Title"})
    title = clean_text(h1.get_text(" ") if h1 else meta_title["content"] if meta_title else soup.title.get_text(" "))
    switch = [normalise_url(a["href"]) for a in soup.find_all("a", href=True) if a.get_text(strip=True) in ("DE", "EN", "FR")]
    text = clean_text(raw)
    ptype = page_type(t, path)
    return Page(url, host, lang, ptype, title, date and datetime.strptime(date["content"], t.date_format).date().isoformat(),
                text, hashlib.sha256(text.encode()).hexdigest(), lang_links=[u for u in switch if u != url],
                people=person_entries(main, url, t))


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
    units = {host_short(h.name): Unit(host_short(h.name), h.label, h.role or "institute", None, h.name) for h in domain.hosts}
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


def collect_people(pages: list[Page], unit_names: dict[str, str], fetched: set[str]) -> list[dict]:
    """One row per person and unit. Member lists come first, so a person belongs to the group that lists them;
    their own page adds what the list lacks. English pages first, so English profile links win. A profile link
    is kept only for a page fetched with HTTP 200, so every link shown is checked (D-26)."""
    rows: dict[tuple[str, str], dict] = {}
    by_profile: dict[str, list[dict]] = {}
    for p in sorted(pages, key=lambda p: (any(e["own_page"] for e in p.people), p.lang != "en", p.url)):
        for e in p.people:
            name, titles = split_name(e["name"])
            if not name:   # the source page lists titles in the name field (D-20)
                print(f"person entry without a name, left out: {e['name']!r} on {p.url}")
                continue
            profile = e["profile_url"] if e["profile_url"] in fetched else None
            new = dict(unit_id=p.unit_id, name=name, titles=titles, function=e["function"] and clean_text(e["function"]),
                       affiliation=e["affiliation"] and clean_text(e["affiliation"]), email=e["email"], phone=e["phone"],
                       profile_url=profile, source_url=p.url)
            listed = e["own_page"] and by_profile.get(profile) or [rows.setdefault((p.unit_id, match_key(name)), new)]
            if profile and not e["own_page"]:
                by_profile.setdefault(profile, []).append(listed[0])
            for r in listed:
                r.update({k: v for k, v in new.items() if r[k] is None and v is not None})
    for i, r in enumerate(rows.values()):   # position: order on the member list, where the head comes first
        r["position"] = i
        r["affiliation"] = r["affiliation"] or unit_names[r["unit_id"]]
        r["contact"] = bool(r["function"] and LEAD_ROLE.search(r["function"]))
    return list(rows.values())


def load_pages(conn, domain: Domain) -> list[Page]:
    hosts = {h.name: domain.templates[h.template] for h in domain.hosts}
    rows = conn.execute("SELECT url, host, raw_path FROM dataset.pages WHERE status = 200 AND gone_at IS NULL "
                        "AND host = ANY(%s) ORDER BY url", (list(hosts),)).fetchall()
    assert rows, "dataset is empty; run navigator fetch"
    rows = [r for r in rows if domain.host(r["host"]).allows(urlsplit(r["url"]).path)]
    raw = lambda r: (ROOT / r["raw_path"]).read_text(encoding="utf-8")
    pages = [parse_wordpress(domain, r["host"], r["url"], json.loads(raw(r))) if hosts[r["host"]].wp_api
             else parse_html(domain, r["host"], r["url"], raw(r)) for r in rows]
    return [p for p in pages if p]


def run(conn, domain: Domain) -> dict:
    pages = flagged_check(dedupe(domain, load_pages(conn, domain)))
    units = assign_units(domain, pages)              # before the word filter: a short index page still defines its unit
    pages = [p for p in pages if words(p.text) >= MIN_WORDS]
    units = apply_aliases([u for u in units if u.id in {p.unit_id for p in pages}], pages)
    english = {p.url for p in pages if p.lang == "en"}
    for p in pages:   # a German or French page points to its English version (spec 5.2)
        p.translation_of = next((u for u in p.lang_links if u in english), None) if p.lang != "en" else None
    people = collect_people(pages, {u.id: u.name for u in units}, {r["url"] for r in conn.execute(
        "SELECT url FROM dataset.pages WHERE status = 200 AND gone_at IS NULL")})
    items = [dict(unit_id=p.unit_id, kind=p.page_type, name=p.title, url=p.url)
             for p in pages if p.page_type in ("project", "facility")]
    out = {"pages": [asdict(p) for p in pages], "units": [asdict(u) for u in units], "people": people, "items": items}
    assert len({u.id for u in units}) == len(units), "unit ids are not unique"
    assert {p.unit_id for p in pages} <= {u.id for u in units}
    print(f"extract: {len(pages)} pages, {len(units)} units, {len(people)} people, {len(items)} items")
    return out
