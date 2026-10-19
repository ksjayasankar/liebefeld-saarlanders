"""Spec section 4: support check of a generated sentence against quoted source lines (Apertus 70B, D-05, D-22)."""
from . import apertus
from .config import env

SYSTEM = ("You check whether quoted source lines fully support a claim. A claim with any detail that no line states "
          "is not supported.")
INSTRUCTION = """Claim: {claim}
The quoted lines are numbered 1 to {n}.
Return: {{"lines": [at most 10 numbers of the lines that together support every detail of the claim]}}
Return {{"lines": []}} if the claim is not fully supported."""


def supporting_lines(conn, claim: str, sources: list[str]) -> list[int]:
    """The 1-based numbers of the source lines that support the claim; empty when it is not supported."""
    return apertus.call(conn, env("LLM_NAME_LARGE"), SYSTEM, sources, INSTRUCTION.format(claim=claim, n=len(sources)), apertus.Support, 0.0, 400).lines
