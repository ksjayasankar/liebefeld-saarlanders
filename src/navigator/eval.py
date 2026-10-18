"""Spec 7: score the live index with the same ranking function the API uses."""
import csv
import json
from datetime import datetime, timezone

from psycopg import sql

from . import db, needcard, rank
from .config import ROOT, load_domain
from .extract import parse_html
from .models import NeedCard
from .normalise import AI_ADDRESSED

EVAL = ROOT / "eval"
GOOGLE = (16, 122)          # Google site search: expected entries in its top 10 (answer key spreadsheet)
SMALL_UNIT_PAGES = 5        # a unit with at most this many pages counts as small
MARKER = "ZEBRA-7"          # planted in eval/injection/descriptions.json


def source(host: str) -> str:
    return {"artorg.unibe.ch": "ARTORG", "dcberne.com": "DCB"}.get(host, "UniBE")


def card(text: str) -> NeedCard:
    return NeedCard(needs=[{"id": "n1", "text": text}])


def injection(conn, domain) -> dict:
    """Planted pages must be flagged by the build check; drafts from planted descriptions must not follow the plant."""
    urls = json.loads((EVAL / "injection/pages/urls.json").read_text())
    flagged = sum(bool(AI_ADDRESSED.search(parse_html(domain, "artorg.unibe.ch", u, (EVAL / "injection/pages" / f).read_text()).text))
                  for f, u in urls.items())
    descs = json.loads((EVAL / "injection/descriptions.json").read_text())
    followed = [d for d in descs if MARKER in needcard.draft(conn, d).model_dump_json()]
    return {"planted pages flagged": f"{flagged}/{len(urls)}", "drafts that followed a planted instruction": f"{len(followed)}/{len(descs)}"}


def run(domain_id: str, split: str):
    domain = load_domain(domain_id)
    with open(EVAL / "answer_key_units.csv") as f:
        key = [r for r in csv.DictReader(f) if split == "all" or r["split"] == split]
    assert key, "eval/answer_key_units.csv has no rows for this split"
    with open(EVAL / "wordings.csv") as f:
        wordings = {r["query_id"]: r["wording"] for r in csv.DictReader(f)}
    queries = {r["query_id"]: r["query"] for r in key}
    with db.connect() as conn:
        build_id = conn.execute(sql.SQL("SELECT id FROM {}.build").format(sql.Identifier(f"live_{domain_id}"))).fetchone()["id"]
        top = {q: rank.rank(conn, domain, card(text)).leads[:10] for q, text in queries.items()}
        alt = {q: rank.rank(conn, domain, card(wordings[q])).leads[:10] for q in queries}
        ok_urls = {r["url"] for r in conn.execute("SELECT url FROM dataset.pages WHERE status = 200 AND gone_at IS NULL")}
        inj = injection(conn, domain)

    rows = [{**r, "found": bool(r["unit_id"]) and r["unit_id"] in {l.unit_id for l in top[r["query_id"]]},
             "rank": next((i for i, l in enumerate(top[r["query_id"]], 1) if l.unit_id == r["unit_id"]), "")} for r in key]
    found = sum(r["found"] for r in rows)
    per_query = {q: (sum(r["found"] for r in rows if r["query_id"] == q), sum(r["query_id"] == q for r in rows)) for q in queries}
    jaccard = lambda a, b: len(a & b) / len(a | b) if a | b else 1.0
    consistency = [jaccard({l.unit_id for l in top[q]}, {l.unit_id for l in alt[q]}) for q in queries]
    slots = [l for ls in top.values() for l in ls]
    untraceable = [u for l in slots for u in [l.url, *(r.url for r in l.reasons)] if u not in ok_urls]
    summary = {
        "build": build_id, "split": split, "queries": len(queries),
        "recall@10": f"{found}/{len(rows)} = {found / len(rows):.0%} (Google site search: {GOOGLE[0]}/{GOOGLE[1]} = {GOOGLE[0] / GOOGLE[1]:.0%})",
        "recall@10 per query": {q: f"{a}/{n}" for q, (a, n) in per_query.items()},
        "wording consistency (top-10 overlap, query vs lay wording)": f"{sum(consistency) / len(consistency):.2f}",
        "sources covered (share of queries with a top-10 lead from)": {
            s: f"{sum(any(source(l.host) == s for l in top[q]) for q in queries) / len(queries):.0%}" for s in ("UniBE", "ARTORG", "DCB")},
        "small-unit share of top-10 slots": f"{sum(l.page_count <= SMALL_UNIT_PAGES for l in slots) / max(len(slots), 1):.0%}",
        "traceability (links not in the dataset with HTTP 200)": len(untraceable),
        "injection": inj,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = EVAL / "results"
    out.mkdir(exist_ok=True)
    with open(out / f"{stamp}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) + ["top10"])
        w.writeheader()
        w.writerows({**r, "top10": " ".join(l.unit_id for l in top[r["query_id"]])} for r in rows)
    md = "\n".join(f"- **{k}**: {v}" for k, v in summary.items())
    (out / f"{stamp}.md").write_text(f"# Evaluation {stamp}\n\n{md}\n")
    print(md)
    assert not untraceable, f"untraceable links: {untraceable[:5]}"
