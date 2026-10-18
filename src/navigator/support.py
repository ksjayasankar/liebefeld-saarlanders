"""Spec section 4: yes-or-no support check of a generated sentence against its sources (Apertus 8B, decision D-05)."""
from . import apertus
from .config import env

SYSTEM = "You check whether quoted source sentences fully support a claim. Unsupported details mean false."


def check(conn, claim: str, sources: list[str], model_env: str = "APERTUS_8B") -> bool:
    verdict = apertus.call(conn, env(model_env), SYSTEM, sources, f'Claim: {claim}\nReturn: {{"supported": true or false}}',
                           apertus.Verdict, 0.0, 10)
    return verdict.supported
