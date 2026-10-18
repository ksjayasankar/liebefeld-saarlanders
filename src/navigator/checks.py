"""Spec 5.9: a build goes live only if every check passes. Each check lists its offending rows."""
import csv

from psycopg import sql

from . import embed
from .config import CATEGORIES, ROOT, Domain, load_yaml
from .normalise import AI_ADDRESSED, CONTACT_RE

SQL_CHECKS = {
    "every unit has at least one page chunk":
        "SELECT id FROM units u WHERE NOT EXISTS (SELECT 1 FROM chunks c WHERE c.unit_id = u.id AND NOT c.is_terms)",
    "every summary source is a page of the build, and the category is one of the six":
        "SELECT id FROM units WHERE NOT summary_sources <@ ARRAY(SELECT url FROM pages) OR NOT category = ANY(%(categories)s)",
    "every URL is on a domain host, in the dataset with HTTP 200, and not gone":
        "SELECT p.url FROM pages p LEFT JOIN dataset.pages d USING (url) "
        "WHERE d.status IS DISTINCT FROM 200 OR d.gone_at IS NOT NULL OR NOT p.host = ANY(%(hosts)s)",
    "every report sentence has a source page in the build":
        "SELECT section, position FROM report_sentences r WHERE NOT EXISTS (SELECT 1 FROM pages p WHERE p.url = r.url)",
    "no two chunks share a text":
        "SELECT md5(text) FROM chunks GROUP BY md5(text) HAVING count(*) > 1",
    "every embedding has length 1":
        "SELECT id FROM chunks WHERE abs(vector_norm(embedding) - 1) > 0.001 "
        "UNION ALL SELECT id FROM units WHERE abs(vector_norm(embedding) - 1) > 0.001",
    "the build row names the model the API loads":
        "SELECT id FROM build WHERE model_id <> %(model)s OR dim <> %(dim)s",
}
SERVED_TEXT = ["SELECT 'unit ' || id, summary FROM units", "SELECT 'chunk ' || id, text FROM chunks",
               "SELECT 'item ' || url, name FROM unit_items", "SELECT 'report ' || section || position, sentence FROM report_sentences"]


def answer_key_units() -> set[str]:
    with open(ROOT / "eval/answer_key_units.csv") as f:
        return {r["unit_id"] for r in csv.DictReader(f)}


def run(conn, domain: Domain, schema: str):
    conn.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema)))
    params = {"categories": list(CATEGORIES), "hosts": [h.name for h in domain.hosts], "model": embed.MODEL_ID, "dim": embed.DIM}
    failures = {name: rows for name, q in SQL_CHECKS.items() if (rows := conn.execute(q, params).fetchall())}
    texts = [r for q in SERVED_TEXT for r in conn.execute(q).fetchall()]
    rows = [k for k, t in (tuple(r.values()) for r in texts) if CONTACT_RE.search(t)]
    if rows:
        failures["no email address or phone number in any text the API serves"] = rows
    cleared = set(load_yaml("flagged_pages.yaml")["cleared"])
    flagged = {r["url"] for r in conn.execute("SELECT url, text FROM chunks WHERE url IS NOT NULL").fetchall()
               if AI_ADDRESSED.search(r["text"])} - cleared
    if flagged:
        failures["every page addressed to an AI system is excluded or cleared"] = sorted(flagged)
    units = {r["id"] for r in conn.execute("SELECT id FROM units").fetchall()}
    if missing := answer_key_units() - units:
        failures["every unit id in eval/answer_key_units.csv exists"] = sorted(missing)
    conn.execute("SET search_path TO public")
    assert not failures, "build checks failed:\n" + "\n".join(f"- {k}: {v[:20]}" for k, v in failures.items())
    print(f"checks: all {len(SQL_CHECKS) + 3} passed on {schema}")
