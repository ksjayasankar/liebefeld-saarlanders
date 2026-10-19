"""D-26: one sentence on why a lead matches, written from its quoted reasons only and checked against them."""
from concurrent.futures import ThreadPoolExecutor

from pydantic import Field

from . import apertus, support
from .config import Strict, env
from .models import Lead

# Issue 68: given the needs as the subject, the 8B model restated them as the unit's work ("designs clinical validation
# studies for the glucose sensor") and the checker rightly dropped the sentence. The needs are now context only.
SYSTEM = ("You tell a business development officer, in one sentence, what a research unit does, using only what the numbered "
          "sentences say about it. Do not describe the company, its product or what the unit could do for it.")
INSTRUCTION = """The company is looking for: {needs}
Return: {{"sentence": "one sentence of at most 35 words about what the unit does, as the numbered sentences state it"}}"""


class Explanation(Strict):
    sentence: apertus.Plain = Field(min_length=10, max_length=300)


def explain(conn, lead: Lead) -> str | None:
    """None when the 70B checker finds no supporting reason sentence; the quotes stay the evidence."""
    lines = [r.sentence for r in lead.reasons]
    needs = "; ".join(r.need_text for r in lead.reasons).replace("<", "‹").replace(">", "›")
    s = apertus.call(conn, env("LLM_NAME"), SYSTEM, lines, INSTRUCTION.format(needs=needs), Explanation, 0.0, 200).sentence
    return s if support.supporting_lines(conn, s, lines) else None


def explain_all(conn, leads: list[Lead], progress=lambda event: None):
    """In parallel; the gateway client limits concurrent calls (LLM_PARALLEL). One progress event per lead, in order."""
    with ThreadPoolExecutor(max(len(leads), 1)) as ex:
        for lead, s in zip(leads, ex.map(lambda l: explain(conn, l), leads)):
            lead.explanation = s
            progress({"step": "explain", "lead": lead.name, "supported": s is not None})
