"""Spec 6.8: the request's report as PDF, in two versions. No text is generated here; every sentence keeps its source.

internal: the agency's review of the findings (all quotes with their live check, all people with contacts).
external: what the agency sends the company (contact persons by name only, quotes still on their page, the sourced
          "support in Bern" sections). Layout after finalreport/*.tex."""
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from urllib.request import url2pathname

from jinja2 import Environment, FileSystemLoader, select_autoescape
from psycopg import sql

from .config import CATEGORIES, load_domain
from .models import CATEGORY_LABELS, Lead, SearchResult

TEMPLATES = Path(__file__).parent / "templates"
JINJA = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))
TYPES = {".css": "text/css", ".png": "image/png"}
Audience = Literal["internal", "external"]
REJECTED = ("not_relevant", "wrong_topic")   # feedback that keeps a lead out of the company's report
LIVE = {"found": "still on the page", "changed": "no longer on the page", "gone": "page gone",
        "unreachable": "page did not answer", "not_checked": "not checked live"}


def fetcher():
    """Serves only our own template files; any other URL stops the rendering (spec section 4)."""
    from weasyprint.urls import FatalURLFetchingError, URLFetcher, URLFetcherResponse

    class OwnFilesOnly(URLFetcher):
        def fetch(self, url, headers=None):
            path = Path(url2pathname(urlsplit(url).path)).resolve()
            if not (url.startswith("file://") and path.parent == TEMPLATES and path.is_file() and path.suffix in TYPES):
                raise FatalURLFetchingError(f"report may not fetch {url}")
            return URLFetcherResponse(url, body=path.read_bytes(), headers={"Content-Type": TYPES[path.suffix]})

    return OwnFilesOnly()


class Notes:
    """Numbered footnotes; every sentence in the report is added with its source URL."""
    def __init__(self):
        self.urls: list[str] = []

    def __call__(self, text: str, url: str) -> dict:
        assert text and url, f"report sentence without a source: {text!r}"
        if url not in self.urls:
            self.urls.append(url)
        return {"text": text, "n": self.urls.index(url) + 1}


def render(conn, request_id, audience: Audience) -> bytes:
    row = conn.execute("SELECT * FROM app.requests WHERE id = %s", (request_id,)).fetchone()
    res = SearchResult(**row["leads"])
    live = sql.Identifier(f"live_{row['domain']}")
    sources = {r["id"]: r["summary_sources"] for r in conn.execute(
        sql.SQL("SELECT id, summary_sources FROM {}.units WHERE id = ANY(%s)").format(live),
        ([l.unit_id for g in res.groups for l in g.leads],))}
    report = conn.execute(sql.SQL("SELECT * FROM {}.report_sentences ORDER BY section, position").format(live)).fetchall()
    rejected = {r["unit_id"] for r in conn.execute("SELECT unit_id FROM app.feedback WHERE request_id = %s AND action = ANY(%s)",
                                                    (request_id, list(REJECTED)))}
    return pdf(html(res, sources, report, load_domain(row["domain"]), row["created_at"], audience, rejected))


def card(lead: Lead, summary_url: str, note: Notes, audience: Audience) -> dict:
    # The company only sees quotes the live check did not find changed or gone (D-32); the agency sees them all, flagged.
    reasons = [r for r in lead.reasons if audience == "internal" or r.live not in ("changed", "gone")]
    # The explanation was checked against the quoted reasons, so it points to the first of them. Notes are taken in
    # reading order; the company sees the summary only when there is no explanation.
    explanation = note(lead.explanation, lead.reasons[0].url) if lead.explanation and lead.reasons else None
    summary = note(lead.summary, summary_url) if audience == "internal" or not explanation else None
    quotes = [{"need": r.need_text, "live": LIVE.get(r.live), "warn": r.live in ("changed", "gone"), **note(r.sentence, r.url)}
              for r in reasons]
    return {"lead": lead, "summary": summary, "explanation": explanation, "quotes": quotes,
            "people": lead.people if audience == "internal" else [p for p in lead.people if p.contact]}


def html(res: SearchResult, sources: dict[str, list[str]], report: list[dict], domain, created, audience: Audience,
         rejected: set[str] = frozenset()) -> str:
    """rejected: units staff marked not relevant; the agency sees them flagged, the company does not see them."""
    note = Notes()
    kept = [(g.label, [l for l in g.leads if audience == "internal" or l.unit_id not in rejected]) for g in res.groups]
    groups = [{"label": label, "cards": [{**card(l, sources[l.unit_id][0], note, audience), "rejected": l.unit_id in rejected}
                                         for l in ls]} for label, ls in kept if ls]
    leads = [l for _, ls in kept for l in ls]
    touched = {l.category for l in leads}
    sections = [{"title": sec.title, "sentences": [note(r["sentence"], r["url"]) for r in report if r["section"] == key]}
                for key, sec in domain.report_sections.items() if key not in CATEGORIES or key in touched] if audience == "external" else []
    per_need = {n.id: sum(n.id in l.need_ids for l in leads) for n in res.card.needs}
    return JINJA.get_template(f"report_{audience}.html").render(res=res, groups=groups, sections=[s for s in sections if s["sentences"]],
                                                                per_need=per_need, notes=note.urls, created=created,
                                                                categories=CATEGORY_LABELS)


def pdf(document: str) -> bytes:
    from weasyprint import HTML
    return HTML(string=document, base_url=TEMPLATES.as_uri() + "/", url_fetcher=fetcher()).write_pdf()
