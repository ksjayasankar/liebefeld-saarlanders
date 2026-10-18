"""Spec 5.5: concepts from the vocabulary files, and tagging text with them (same code at build and request time).

Vocabulary file format (assumed until synonyms.json is seen, decision D-08):
{"<concept id>": {"source": "mesh|wikidata", "labels": {"en": [...], "de": [...], "fr": [...]}}}
"""
import json
from collections import defaultdict

from .config import ROOT, Domain, load_yaml
from .normalise import match_key


def load(domain: Domain) -> tuple[list[dict], list[dict]]:
    concepts, labels = {}, []
    for path in domain.vocabularies:
        for cid, c in json.loads((ROOT / path).read_text()).items():
            assert cid not in concepts, f"duplicate concept id {cid}"
            concepts[cid] = {"id": cid, "source": c["source"]}
            rows = [{"concept_id": cid, "lang": lang, "label": label, "match_key": match_key(label)}
                    for lang, ls in c["labels"].items() for label in ls]
            assert rows and all(r["match_key"] for r in rows), f"concept {cid} has no or empty labels"
            labels += rows
    return list(concepts.values()), resolve(labels)


def resolve(labels: list[dict]) -> list[dict]:
    """Labels pointing to several concepts must be resolved by hand in config/concept_overrides.yaml."""
    owners = defaultdict(set)
    for r in labels:
        owners[r["match_key"]].add(r["concept_id"])
    overrides = load_yaml("concept_overrides.yaml")
    open_ = sorted(k for k, cs in owners.items() if len(cs) > 1 and k not in overrides)
    assert not open_, f"ambiguous labels; resolve in config/concept_overrides.yaml: {open_}"
    return [r for r in labels if len(owners[r["match_key"]]) == 1 or overrides[r["match_key"]] == r["concept_id"]]


def index(labels: list[dict]) -> dict[tuple[str, ...], str]:
    return {tuple(r["match_key"].split()): r["concept_id"] for r in labels}


def tag(text: str, idx: dict[tuple[str, ...], str]) -> set[str]:
    """Concepts whose labels occur in the text, longest match first; matched words are not reused."""
    tokens, used, found = match_key(text).split(), set(), set()
    for n in sorted({len(k) for k in idx}, reverse=True):
        for i in range(len(tokens) - n + 1):
            span = set(range(i, i + n))
            if not span & used and (cid := idx.get(tuple(tokens[i:i + n]))):
                found.add(cid)
                used |= span
    return found
