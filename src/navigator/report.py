"""Spec 6.8: the request's report as PDF. No text is generated here; every sentence keeps its source."""
import io
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

import matplotlib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from psycopg import sql

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402

from .config import CATEGORIES, load_domain  # noqa: E402
from .models import CATEGORY_LABELS, SearchResult  # noqa: E402

TEMPLATES = Path(__file__).parent / "templates"
JINJA = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))


def fetcher():
    """Serves only our own template files; any other URL stops the rendering (spec section 4)."""
    from weasyprint.urls import FatalURLFetchingError, URLFetcher, URLFetcherResponse

    class OwnFilesOnly(URLFetcher):
        def fetch(self, url, headers=None):
            path = Path(url2pathname(urlsplit(url).path)).resolve()
            if not (url.startswith("file://") and path.parent == TEMPLATES and path.is_file()):
                raise FatalURLFetchingError(f"report may not fetch {url}")
            return URLFetcherResponse(url, body=path.read_bytes(), headers={"Content-Type": "text/css"})

    return OwnFilesOnly()


def source_group(host: str) -> str:
    return {"artorg.unibe.ch": "ARTORG", "dcberne.com": "DCB"}.get(host, "UniBE")


def bar_svg(counts: dict[str, int], title: str) -> Markup:
    """Horizontal bar chart as inline SVG. Labels are fixed category or need ids, never outside text."""
    fig, ax = plt.subplots(figsize=(6.2, 0.5 + 0.42 * len(counts)))
    labels, values = list(counts)[::-1], list(counts.values())[::-1]
    ax.barh(labels, values, color="#3b6e8f")
    for y, v in enumerate(values):
        ax.text(v + 0.05, y, str(v), va="center", fontsize=9)
    ax.set_title(title, fontsize=10, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_visible(False)
    fig.tight_layout()
    buf = io.StringIO()
    fig.savefig(buf, format="svg")
    plt.close(fig)
    return Markup(buf.getvalue()[buf.getvalue().index("<svg"):])


class Notes:
    """Numbered footnotes; every sentence in the report is added with its source URL."""
    def __init__(self):
        self.urls: list[str] = []

    def __call__(self, text: str, url: str) -> dict:
        assert text and url, f"report sentence without a source: {text!r}"
        if url not in self.urls:
            self.urls.append(url)
        return {"text": text, "n": self.urls.index(url) + 1}


def render(conn, request_id) -> bytes:
    row = conn.execute("SELECT * FROM app.requests WHERE id = %s", (request_id,)).fetchone()
    res = SearchResult(**row["leads"])
    live = sql.Identifier(f"live_{row['domain']}")
    sources = {r["id"]: r["summary_sources"] for r in conn.execute(
        sql.SQL("SELECT id, summary_sources FROM {}.units WHERE id = ANY(%s)").format(live),
        ([l.unit_id for g in res.groups for l in g.leads],))}
    report = conn.execute(sql.SQL("SELECT * FROM {}.report_sentences ORDER BY section, position").format(live)).fetchall()
    return pdf(html(res, sources, report, load_domain(row["domain"]), row["created_at"]))


def html(res: SearchResult, sources: dict[str, list[str]], report: list[dict], domain, created) -> str:
    leads = [l for g in res.groups for l in g.leads]
    touched = {l.category for l in leads}
    note = Notes()
    cards = [{"lead": l, "summary": note(l.summary, sources[l.unit_id][0]),
              "reasons": [{"need": r.need_text, **note(r.sentence, r.url)} for r in l.reasons]} for l in leads]
    sections = [{"title": sec.title, "sentences": [note(r["sentence"], r["url"]) for r in report if r["section"] == key]}
                for key, sec in domain.report_sections.items() if key not in CATEGORIES or key in touched]
    per_need = {n.id: sum(n.id in l.need_ids for l in leads) for n in res.card.needs}
    figures = [bar_svg(per_need, "Leads answering each need"),
               bar_svg({CATEGORY_LABELS[c]: n for c, n in Counter(l.category for l in leads).items()}, "Leads per category"),
               bar_svg(dict(Counter(source_group(l.host) for l in leads)), "Leads by source")]
    return JINJA.get_template("report.html").render(res=res, cards=cards, sections=sections, figures=figures, per_need=per_need,
                                                    notes=note.urls, domain=domain, created=created)


def pdf(document: str) -> bytes:
    from weasyprint import HTML
    return HTML(string=document, base_url=TEMPLATES.as_uri() + "/", url_fetcher=fetcher()).write_pdf()
