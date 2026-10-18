"""D-26: one sentence on why a lead matches, written from its quoted reasons only and checked against them."""
from concurrent.futures import ThreadPoolExecutor

from pydantic import Field

from . import apertus, support
from .config import Strict, env
from .models import Lead

SYSTEM = ("You explain to a business development officer, in one sentence, what a research unit does that answers "
          "a company's needs. State only what the numbered sentences say.")
INSTRUCTION = """Needs: {needs}
Return: {{"sentence": "one sentence of at most 35 words about the unit"}}"""


class Explanation(Strict):
    sentence: apertus.Plain = Field(min_length=10, max_length=300)


def explain(conn, lead: Lead) -> str | None:
    """None when the 70B checker finds no supporting reason sentence; the quotes stay the evidence."""
    lines = [r.sentence for r in lead.reasons]
    needs = "; ".join(r.need_text for r in lead.reasons).replace("<", "‹").replace(">", "›")
    s = apertus.call(conn, env("APERTUS_8B"), SYSTEM, lines, INSTRUCTION.format(needs=needs), Explanation, 0.0, 200).sentence
    return s if support.supporting_lines(conn, s, lines) else None


def explain_all(conn, leads: list[Lead]):
    """In parallel; the gateway client limits concurrent calls (APERTUS_PARALLEL)."""
    with ThreadPoolExecutor(max(len(leads), 1)) as ex:
        for lead, s in zip(leads, ex.map(lambda l: explain(conn, l), leads)):
            lead.explanation = s
