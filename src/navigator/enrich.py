"""Spec 5.4: unit summaries, plain-language terms and lead category from the unit's own sentences."""
from concurrent.futures import ThreadPoolExecutor

from . import apertus, db, support
from .config import env
from .normalise import sentences

MAX_SENTENCES = 60
ORDER = {"group": 0, "project": 1, "facility": 2, "other": 3, "news": 4, "members": 5, "person": 6}
SYSTEM = ("You describe university research units for companies. Use only the numbered sentences provided. "
          "Leave out anything they do not support.")
INSTRUCTION = """Unit: {name}
Return: {{"summary": "two plain English sentences",
         "summary_sources": [sentence numbers],
         "terms": {{"en": [...], "de": [...], "fr": [...]}},
         "category": "research_partner|facility|clinical_validation|licensing|support|talent"}}
Terms: 10 to 20 words or short phrases a company might use for this work,
including everyday words and abbreviations."""


def unit_sentences(unit_pages: list[dict]) -> list[tuple[str, str]]:
    """(sentence, url) pairs: group page first, then projects, facilities and the rest; no repeats."""
    seen, out = set(), []
    for p in sorted(unit_pages, key=lambda p: (ORDER[p["page_type"]], p["lang"] != "en", p["url"])):
        for s in sentences(p["text"]):
            if s not in seen and len(out) < MAX_SENTENCES:
                seen.add(s)
                out.append((s, p["url"]))
    return out


def enrich_unit(conn, unit: dict, unit_pages: list[dict]) -> dict:
    numbered = unit_sentences(unit_pages)
    assert numbered, f"unit {unit['id']} has no sentences"
    lines = [s for s, _ in numbered]
    a = apertus.call(conn, env("APERTUS_8B"), SYSTEM, lines, INSTRUCTION.format(name=unit["name"]), apertus.UnitSummary, 0.2, 700)
    cited = [lines[i - 1] for i in a.summary_sources]
    verdicts = [(s, support.check(conn, s, cited)) for s in sentences(a.summary) or [a.summary]]
    accepted = [s for s, ok in verdicts if ok]
    assert accepted, f"unit {unit['id']}: no summary sentence passed the support check: {a.summary!r}"
    return {"summary": " ".join(accepted), "summary_sources": sorted({numbered[i - 1][1] for i in a.summary_sources}),
            "terms": a.terms.model_dump(), "category": a.category, "rejected": [s for s, ok in verdicts if not ok]}


def run(extracted: dict) -> dict[str, dict]:
    by_unit = {}
    for p in extracted["pages"]:
        by_unit.setdefault(p["unit_id"], []).append(p)

    def one(unit):
        with db.connect() as conn:
            return unit["id"], enrich_unit(conn, unit, by_unit[unit["id"]])

    with ThreadPoolExecutor(int(env("APERTUS_PARALLEL"))) as ex:
        out = dict(ex.map(one, extracted["units"]))
    rejected = {u: e["rejected"] for u, e in out.items() if e["rejected"]}
    print(f"enrich: {len(out)} units; summary sentences rejected by the support check: {rejected}")
    return out
