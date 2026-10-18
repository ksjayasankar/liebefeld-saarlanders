"""Spec 6.3: the one ranking function, called by the search endpoint and by the evaluation."""
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
from psycopg import sql

from . import apertus, concepts, embed
from .config import Domain, env
from .models import CATEGORY_LABELS, Item, Lead, LeadGroup, NeedCard, Person, Reason
from .normalise import sentences

POOL, RRF_K, CONCEPT_BOOST, BEST_CHUNKS = 200, 60, 0.01, 3
SHORTLIST, DIVERSITY, TIE_BAND = 10, 0.2, 0.05   # tie band relative to the best gain
CANDIDATE_SHARE = 0.05  # a unit is a candidate if its best page chunk reaches this share of the need's best chunk score
COVER = 0.8   # coverage probability of a unit scored 1: the best unit leaves 20% of a need open, so relevance keeps ordering
LIKE, DISLIKE = 0.75, 0.15
STALE_AFTER = timedelta(days=3 * 365)
CONTACTS, PEOPLE, PERSON_SHARE = 3, 6, 0.5   # a person's own page matches a need if a sentence scores half the lead's best chunk
PERSON_PAGES = 5   # per need and lead, the person pages closest to the need go to the reranker
STEMMERS = ("english", "german", "french")
EXPAND_SYSTEM = "List the words researchers and companies use for this need, including abbreviations and everyday words."
EXPAND_INSTRUCTION = 'Need: the quoted line [1]\nReturn: {"en": [...], "de": [...], "fr": [...]}\nGive 5 to 15 terms per language, each 1 to 4 words.'


@dataclass
class Adjust:
    """What feedback changed for one request (spec 6.5)."""
    liked: dict[str, list[str]] = field(default_factory=dict)       # need id -> unit ids
    rejected: dict[str, list[str]] = field(default_factory=dict)
    hidden: set[str] = field(default_factory=set)
    category_weight: dict[str, float] = field(default_factory=dict)
    hide_stale: bool = False


@dataclass
class Ranked:
    leads: list[Lead]
    groups: list[LeadGroup]
    covered: list[str]
    uncovered: list[str]
    coverage_line: str


def expand(conn, text: str) -> list[str]:
    e = apertus.call(conn, env("APERTUS_8B"), EXPAND_SYSTEM, [text], EXPAND_INSTRUCTION, apertus.Expansion, 0.0, 400)
    return e.en + e.de + e.fr


def select(scores: np.ndarray, sims: np.ndarray, pages: np.ndarray, k: int) -> list[int]:
    """Greedy coverage: a unit gains for each need what the picked units leave uncovered, minus a near-duplicate
    penalty; among units within TIE_BAND (relative) of the best gain the one with the fewest pages wins (fair tie-break)."""
    scores, picked = scores * COVER, []
    for _ in range(min(k, len(scores))):
        residual = np.prod(1 - scores[picked], axis=0) if picked else np.ones(scores.shape[1])
        gain = (scores * residual).sum(axis=1) - DIVERSITY * (sims[:, picked].max(axis=1) if picked else 0)
        gain[picked] = -np.inf
        band = np.flatnonzero(gain >= gain.max() - TIE_BAND * abs(gain.max()))
        picked.append(int(min(band, key=lambda i: (pages[i], i))))
    return picked


def candidates(conn, text: str, terms: list[str], labels: list[str], vec: np.ndarray, need_concepts: set[str]) -> dict[str, float]:
    """Chunk id -> fused score from keyword search, vector search and shared concepts."""
    phrases = text.split() + terms + labels
    tsq = lambda cfg: sql.SQL(" || ").join(sql.SQL("plainto_tsquery({}, %s)").format(sql.Literal(cfg)) for _ in phrases)
    per_lang = sql.SQL(" UNION ALL ").join(   # one query per language so the GIN index is used
        sql.SQL("(SELECT id, ts_rank_cd(tsv, q) AS r FROM chunks, (SELECT {} AS q) t WHERE lang = {} AND tsv @@ q)").format(tsq(cfg), sql.Literal(lang))
        for lang, cfg in zip(("en", "de", "fr"), STEMMERS))
    kw = conn.execute(sql.SQL("SELECT id FROM ({}) m ORDER BY r DESC, id LIMIT %s").format(per_lang), phrases * 3 + [POOL]).fetchall()
    conn.execute(f"SET hnsw.ef_search = {POOL}")
    vv = conn.execute("SELECT id FROM chunks ORDER BY embedding <=> %s, id LIMIT %s", (vec, POOL)).fetchall()
    fused: dict[str, float] = {}
    for hits in (kw, vv):
        for r, row in enumerate(hits, 1):
            fused[row["id"]] = fused.get(row["id"], 0.0) + 1 / (RRF_K + r)
    if need_concepts:
        for row in conn.execute("SELECT chunk_id, count(*) AS n FROM chunk_concepts WHERE chunk_id = ANY(%s) AND concept_id = ANY(%s) "
                                "GROUP BY chunk_id", (list(fused), list(need_concepts))):
            fused[row["chunk_id"]] += CONCEPT_BOOST * row["n"]
    return fused


def rank(conn, domain: Domain, card: NeedCard, adjust: Adjust | None = None) -> Ranked:
    adjust = adjust or Adjust()
    conn.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(f"live_{domain.id}")))
    labels = conn.execute("SELECT concept_id, match_key FROM concept_labels").fetchall()
    idx = concepts.index(labels)
    unit_rows = {r["id"]: r for r in conn.execute(
        "SELECT u.id, u.name, p.name AS parent, u.host, u.kind, u.category, u.summary, u.terms, u.page_count, u.embedding "
        "FROM units u LEFT JOIN units p ON p.id = u.parent_id")}
    need_vecs = embed.cached(conn, [n.text for n in card.needs])
    unit_scores: dict[str, dict[str, float]] = {}   # need id -> unit id -> score (scaled 0..1)
    best_chunk: dict[tuple[str, str], tuple[float, str]] = {}   # (need, unit) -> best reranked page chunk
    raw_best: dict[str, float] = {}
    for need, v in zip(card.needs, need_vecs):
        v = v + LIKE * _mean(unit_rows, adjust.liked.get(need.id), v) - DISLIKE * _mean(unit_rows, adjust.rejected.get(need.id), v)
        tags = concepts.tag(need.text, idx)
        tag_labels = [r["match_key"] for r in labels if r["concept_id"] in tags]
        fused = candidates(conn, need.text, expand(conn, need.text), tag_labels, v / np.linalg.norm(v), tags)
        rows = {r["id"]: r for r in conn.execute("SELECT id, unit_id, text, is_terms FROM chunks WHERE id = ANY(%s)", (list(fused),))}
        top, per = [], {}   # at most BEST_CHUNKS per unit go to the reranker, so the pool spans many units
        for c in sorted(fused, key=lambda c: (-fused[c], c)):
            u = rows[c]["unit_id"]
            if per.get(u, 0) < BEST_CHUNKS and len(top) < int(env("RERANK_TOP")):
                top.append(c)
                per[u] = per.get(u, 0) + 1
        scores = embed.rerank(need.text, [rows[c]["text"] for c in top])
        per_unit: dict[str, list[float]] = {}
        for c, s in zip(top, scores):
            u = rows[c]["unit_id"]
            if u in adjust.hidden or unit_rows[u]["kind"] == "news":   # a news host is never a lead
                continue
            per_unit.setdefault(u, []).append(float(s))
            if not rows[c]["is_terms"] and s > best_chunk.get((need.id, u), (-1.0, ""))[0]:
                best_chunk[(need.id, u)] = (float(s), c)
        raw = {u: sum(sorted(ss, reverse=True)[:BEST_CHUNKS]) * adjust.category_weight.get(unit_rows[u]["category"], 1.0)
               for u, ss in per_unit.items()}
        top_raw = max(raw.values(), default=0.0)
        unit_scores[need.id] = {u: s / top_raw for u, s in raw.items()} if top_raw else {}
        raw_best[need.id] = max((max(ss) for ss in per_unit.values()), default=0.0)

    leads = []
    units = sorted({u for (n, u), (score, _) in best_chunk.items() if score >= CANDIDATE_SHARE * raw_best[n]})
    if units:
        scores = np.array([[unit_scores[n.id].get(u, 0.0) for n in card.needs] for u in units])
        vecs = np.stack([unit_rows[u]["embedding"].to_numpy() for u in units])
        picked = select(scores, vecs @ vecs.T, np.array([unit_rows[u]["page_count"] for u in units]), SHORTLIST)
        leads = [_lead(conn, card, unit_rows[units[i]], best_chunk, scores[i], need_vecs) for i in picked]
        leads = [l for l in leads if not (adjust.hide_stale and l.stale)]
    threshold = domain.coverage_threshold
    covered = [n.id for n in card.needs if raw_best[n.id] >= threshold]
    uncovered = [n.id for n in card.needs if raw_best[n.id] < threshold]
    text = {n.id: n.text for n in card.needs}
    line = "Covered: " + ("; ".join(text[n] for n in covered) or "none")
    line += (". No lead found for: " + "; ".join(text[n] for n in uncovered)) if uncovered else "."
    groups = [LeadGroup(category=c, label=label, leads=[l for l in leads if l.category == c])
              for c, label in CATEGORY_LABELS.items() if any(l.category == c for l in leads)]
    return Ranked(leads, groups, covered, uncovered, line)


def _mean(unit_rows: dict, unit_ids: list[str] | None, like: np.ndarray) -> np.ndarray:
    return np.mean([unit_rows[u]["embedding"].to_numpy() for u in unit_ids], axis=0) if unit_ids else np.zeros_like(like)


def _quote(need, text: str, url: str) -> Reason:
    """The sentence of a chunk (title line left out) that the reranker finds closest to the need."""
    body = sentences(text.split("\n", 1)[-1]) or [text]
    return Reason(need_id=need.id, need_text=need.text, sentence=body[int(np.argmax(embed.rerank(need.text, body)))], url=url)


def _bio(text: str) -> list[str]:
    """Full sentences of a person's page: headings such as the group name are no evidence about the person."""
    return [s for s in sentences(text.split("\n", 1)[-1]) if len(s.split()) >= 6 and s[-1] in ".!?"]


def _people(conn, card: NeedCard, unit_id: str, best_chunk: dict, need_vecs: list) -> list[Person]:
    """Contact persons first (in list order), then people whose own page has a sentence matching a need: per need, the
    full sentences of the closest person pages are reranked against the lead's best chunk score (D-26)."""
    rows = conn.execute("SELECT * FROM people WHERE unit_id = %s ORDER BY position", (unit_id,)).fetchall()
    reason: dict[str, tuple[float, Reason]] = {}
    for need, v in zip(card.needs, need_vecs):
        if (need.id, unit_id) not in best_chunk:
            continue
        hits = conn.execute("SELECT url, text FROM (SELECT DISTINCT ON (url) url, text, embedding <=> %s AS d FROM chunks "
                            "WHERE url = ANY(%s) ORDER BY url, d) c ORDER BY d LIMIT %s",
                            (v, [r["profile_url"] for r in rows if r["profile_url"]], PERSON_PAGES)).fetchall()
        bio = [(h["url"], s) for h in hits for s in _bio(h["text"])]
        for (url, sentence), s in zip(bio, embed.rerank(need.text, [s for _, s in bio]) if bio else []):
            if s >= PERSON_SHARE * best_chunk[(need.id, unit_id)][0] and s > reason.get(url, (-1.0,))[0]:
                reason[url] = (float(s), Reason(need_id=need.id, need_text=need.text, sentence=sentence, url=url))
    score = lambda r: reason.get(r["profile_url"], (0.0,))[0]
    contacts = [r for r in rows if r["contact"]][:CONTACTS]
    matched = sorted((r for r in rows if r["profile_url"] in reason and r not in contacts), key=score, reverse=True)
    return [Person(**{k: r[k] for k in ("name", "titles", "function", "affiliation", "email", "phone", "profile_url", "source_url", "contact")},
                   reason=reason.get(r["profile_url"], (0.0, None))[1]) for r in (contacts + matched)[:PEOPLE]]


def _lead(conn, card: NeedCard, unit: dict, best_chunk: dict, score_row: np.ndarray, need_vecs: list) -> Lead:
    reasons, dates = [], []
    for need in card.needs:
        if (need.id, unit["id"]) not in best_chunk:
            continue
        chunk = conn.execute("SELECT c.text, c.url, p.page_date FROM chunks c JOIN pages p USING (url) WHERE c.id = %s",
                             (best_chunk[(need.id, unit["id"])][1],)).fetchone()
        reasons.append(_quote(need, chunk["text"], chunk["url"]))
        dates.append(chunk["page_date"])
    items = conn.execute("SELECT kind, name, url FROM unit_items WHERE unit_id = %s ORDER BY kind, name LIMIT 5", (unit["id"],)).fetchall()
    page_date = max((d for d in dates if d), default=None)
    return Lead(unit_id=unit["id"], name=unit["name"], parent=unit["parent"], host=unit["host"], category=unit["category"],
                summary=unit["summary"], expertise=unit["terms"], explanation=None, need_ids=[r.need_id for r in reasons], reasons=reasons,
                items=[Item(**r) for r in items], people=_people(conn, card, unit["id"], best_chunk, need_vecs), page_date=page_date,
                stale=bool(page_date and date.today() - page_date > STALE_AFTER), url=reasons[0].url,
                score=round(float(score_row.sum()), 4), page_count=unit["page_count"])
