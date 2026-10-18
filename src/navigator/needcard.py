"""Spec 6.2: Apertus drafts a need card from a company's public description; each need cites its sentences."""
from . import apertus
from .config import env
from .models import Draft, Need, NeedCard
from .normalise import sentences

SYSTEM = ("You turn a company's public description into a need card for finding research partners in Bern. "
          "Use only the numbered sentences.")
INSTRUCTION = """Return: {"sector": "...", "product": "one line",
         "stage": "idea|prototype|clinical_testing|on_market",
         "needs": [{"text": "one sentence", "category": "research_partner|facility|clinical_validation|licensing|support|talent", "sources": [sentence numbers]}]}
At most 5 needs. Each need must be something a university group, facility or programme could help with."""


def draft(conn, description: str) -> Draft:
    lines = sentences(description)
    assert lines, "the description has no full sentences"
    d = apertus.call(conn, env("APERTUS_8B"), SYSTEM, lines, INSTRUCTION, apertus.NeedCardDraft, 0.2, 700)
    needs = [Need(id=f"n{i}", text=n.text, category=n.category) for i, n in enumerate(d.needs, 1)]
    return Draft(card=NeedCard(sector=d.sector, product=d.product, stage=d.stage, needs=needs), sentences=lines,
                 sources={f"n{i}": n.sources for i, n in enumerate(d.needs, 1)})
