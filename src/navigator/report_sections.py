"""Spec 5.8: public report sections written by Apertus 70B, every sentence checked against its source."""
import re

from . import apertus, support
from .config import Domain, env
from .normalise import sentences

SYSTEM = ("You write one section of a factual location report for a company considering Bern. Use only the numbered "
          "sentences. Every sentence you write cites the one numbered sentence that supports it. No praise, no comparisons.")
INSTRUCTION = """Section: {title}
What it covers: {brief}
Return: {{"sentences": [{{"text": "one plain English sentence", "source": sentence number}}]}}
Write 4 to 8 sentences."""


def run(conn, domain: Domain, pages: list[dict]) -> list[dict]:
    by_url = {p["url"]: p for p in pages}
    banned = re.compile(r"\b(?:" + "|".join(map(re.escape, domain.report_banned)) + r")\b", re.I)
    rows, problems = [], []
    for name, sec in domain.report_sections.items():
        missing = [u for u in sec.sources if u not in by_url]
        assert not missing, f"report section {name}: sources not in the build: {missing}"
        numbered = [(s, u) for u in sec.sources for s in sentences(by_url[u]["text"])]
        lines = [s for s, _ in numbered]
        out = apertus.call(conn, env("APERTUS_70B"), SYSTEM, lines, INSTRUCTION.format(title=sec.title, brief=sec.brief),
                           apertus.ReportSection, 0.2, 1200)
        for pos, s in enumerate(out.sentences, 1):
            source, url = numbered[s.source - 1]
            if not support.check(conn, s.text, [source], "APERTUS_70B") or banned.search(s.text):
                problems.append((name, s.text, source))
            rows.append({"section": name, "position": pos, "sentence": s.text, "url": url, "source_sentence": source})
    assert not problems, "report sentences unsupported or flagged; fix the prompt or the sources:\n" + "\n".join(map(str, problems))
    return rows
