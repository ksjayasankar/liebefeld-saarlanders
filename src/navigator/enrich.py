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
Every detail in the summary must appear in a sentence whose number you list in summary_sources.
Return: {{"summary": "two plain English sentences",
         "summary_sources": [sentence numbers],
         "terms": {{"en": [...], "de": [...], "fr": [...]}},
         "category": "research_partner|facility|clinical_validation|licensing|support|talent"}}
Terms: 10 to 20 words or short phrases a company might use for this work,
including everyday words and abbreviations. Each term is 1 to 4 words, letters and digits only.
Never use these generic words as a term: {generic}."""


def unit_sentences(unit_pages: list[dict]) -> list[tuple[str, str]]:
    """(sentence, url) pairs: group page first, then projects, facilities and the rest, shallow pages first; no repeats."""
    seen, out = set(), []
    for p in sorted(unit_pages, key=lambda p: (ORDER[p["page_type"]], p["url"].count("/"), p["lang"] != "en", p["url"])):
        for s in sentences(p["text"]):
            if s not in seen and len(out) < MAX_SENTENCES:
                seen.add(s)
                out.append((s, p["url"]))
    return out


def enrich_unit(conn, unit: dict, unit_pages: list[dict]) -> dict:
    numbered = unit_sentences(unit_pages)
    assert numbered, f"unit {unit['id']} has no sentences"
    lines = [s for s, _ in numbered]
    a = apertus.call(conn, env("LLM_NAME_LARGE"), SYSTEM, lines, INSTRUCTION.format(name=unit["name"], generic=", ".join(sorted(apertus.GENERIC))), apertus.UnitSummary, 0.2, 1200)
    # The writer under-cites (D-22): the checker reads all of the unit's lines and names the ones that support each sentence.
    verdicts = [(s, support.supporting_lines(conn, s, lines)) for s in sentences(a.summary) or [a.summary]]
    accepted = [(s, found) for s, found in verdicts if found]
    assert accepted, f"unit {unit['id']}: no summary sentence passed the support check: {a.summary!r}"
    return {"summary": " ".join(s for s, _ in accepted),
            "summary_sources": sorted({numbered[i - 1][1] for _, found in accepted for i in found}),
            "terms": a.terms.model_dump(), "category": a.category, "rejected": [s for s, found in verdicts if not found]}


def run(extracted: dict) -> dict[str, dict]:
    by_unit = {}
    for p in extracted["pages"]:
        by_unit.setdefault(p["unit_id"], []).append(p)

    def one(unit):
        with db.connect() as conn:
            try:
                return unit["id"], enrich_unit(conn, unit, by_unit[unit["id"]])
            except AssertionError as e:   # every failing unit is reported, then the run stops
                return unit["id"], e

    with ThreadPoolExecutor(int(env("LLM_PARALLEL"))) as ex:
        out = dict(ex.map(one, extracted["units"]))
    failed = {u: e for u, e in out.items() if isinstance(e, AssertionError)}
    assert not failed, f"enrich: {len(failed)} of {len(out)} units failed; fix the prompt and rerun (the cache keeps the rest):\n" + \
        "\n\n".join(f"== {u}\n{e}" for u, e in failed.items())
    rejected = {u: e["rejected"] for u, e in out.items() if e["rejected"]}
    print(f"enrich: {len(out)} units; summary sentences rejected by the support check: {rejected}")
    return out
