"""Spec 6.2: Apertus drafts a need card from a company's public description; each need cites its sentences."""
from . import apertus
from .config import env
from .models import Draft, Need, NeedCard
from .normalise import AI_ADDRESSED, sentences

SYSTEM = ("You turn a company's public description into a need card for finding research partners in Bern. "
          "Use only the numbered sentences.")
INSTRUCTION = """Return: {"sector": "...", "product": "one line",
         "stage": "idea|prototype|clinical_testing|on_market",
         "needs": [{"text": "one sentence", "category": "research_partner|facility|clinical_validation|licensing|support|talent", "sources": [sentence numbers]}]}
At most 5 needs, only needs the sentences state; every need cites at least one sentence number.
Each need must be something a university group, facility or programme could help with.
One need per need the sentences state, one topic each; keep every one, including regulatory approval and funding.
Each need is searched on its own, so where it helps, name the product's technology and the disease or patients in it, in the sentences' words."""


def draft(conn, description: str) -> Draft:
    """Sentences addressed to an AI system never reach the model (same rule as for pages); the company sees them listed."""
    lines = [s for s in sentences(description) if not AI_ADDRESSED.search(s)]
    ignored = [s for s in sentences(description) if AI_ADDRESSED.search(s)]
    assert lines, "the description has no full sentences about the company"
    d = apertus.call(conn, env("APERTUS_8B"), SYSTEM, lines, INSTRUCTION, apertus.NeedCardDraft, 0.2, 700)
    needs = [Need(id=f"n{i}", text=n.text, category=n.category) for i, n in enumerate(d.needs, 1)]
    return Draft(card=NeedCard(sector=d.sector, product=d.product, stage=d.stage, needs=needs), sentences=lines,
                 sources={f"n{i}": n.sources for i, n in enumerate(d.needs, 1)}, ignored=ignored)
