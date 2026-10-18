"""Spec 5.7: write a build into a fresh staging_<domain> schema, and make it live by renaming schemas."""
import hashlib
from collections import Counter
from datetime import datetime, timezone

import numpy as np
from psycopg import sql
from psycopg.types.json import Jsonb

from . import concepts, embed
from .config import ROOT, Domain
from .db import schema_exists

STEMMER = {"en": "english", "de": "german", "fr": "french"}


def chunk_rows(extracted: dict, enrichment: dict) -> list[dict]:
    """Page chunks, then one term chunk per unit and language; a text that already occurred is not repeated."""
    names = {u["id"]: u["name"] for u in extracted["units"]}
    rows, seen = [], set()
    for p in extracted["pages"]:
        for i, text in enumerate(embed.chunk(p["title"], p["text"])):
            rows.append({"id": f"{hashlib.sha1(p['url'].encode()).hexdigest()[:12]}:{i}", "unit_id": p["unit_id"],
                         "url": p["url"], "lang": p["lang"], "text": text, "is_terms": False})
    for uid, e in enrichment.items():
        for lang, terms in e["terms"].items():
            if terms:
                rows.append({"id": f"{uid}:terms:{lang}", "unit_id": uid, "url": None, "lang": lang,
                             "text": f"{names[uid]}\n" + ", ".join(terms), "is_terms": True})
    unique = [r for r in rows if not (r["text"] in seen or seen.add(r["text"]))]
    print(f"chunks: {len(unique)} ({len(rows) - len(unique)} repeated texts left out)")
    return unique


def build(conn, domain: Domain, extracted: dict, enrichment: dict, report: list[dict]) -> str:
    staging = sql.Identifier(f"staging_{domain.id}")
    conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE; CREATE SCHEMA {}").format(staging, staging))
    conn.execute(sql.SQL("SET search_path TO {}, public").format(staging))
    conn.execute((ROOT / "sql/index_schema.sql").read_text())
    pages, units = extracted["pages"], extracted["units"]
    assert set(enrichment) == {u["id"] for u in units}, "enrichment does not cover exactly the extracted units"

    chunks = chunk_rows(extracted, enrichment)
    vectors = embed.cached(conn, [c["text"] for c in chunks])
    conn.execute(sql.SQL("SET search_path TO {}, public").format(staging))   # embed.cached commits; keep the path explicit
    page_count = Counter(p["unit_id"] for p in pages)
    unit_vec = {}
    for c, v in zip(chunks, vectors):
        unit_vec.setdefault(c["unit_id"], []).append(v)
    unit_vec = {u: (m := np.mean(vs, axis=0)) / np.linalg.norm(m) for u, vs in unit_vec.items()}

    with conn.cursor() as cur:
        cur.executemany("INSERT INTO pages VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        [(p["url"], p["host"], p["lang"], p["page_type"], p["title"], p["page_date"], p["text_hash"],
                          p["translation_of"]) for p in sorted(pages, key=lambda p: p["translation_of"] is not None)])
        cur.executemany("INSERT INTO units VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        [(u["id"], u["name"], u["kind"], u["parent_id"], u["host"], enrichment[u["id"]]["category"],
                          enrichment[u["id"]]["summary"], enrichment[u["id"]]["summary_sources"],
                          enrichment[u["id"]]["terms"]["en"], page_count[u["id"]],
                          unit_vec[u["id"]]) for u in sorted(units, key=lambda u: u["parent_id"] is not None)])
        cur.executemany("INSERT INTO unit_pages VALUES (%s,%s)", [(p["unit_id"], p["url"]) for p in pages])
        cur.executemany("INSERT INTO unit_items VALUES (%(unit_id)s,%(kind)s,%(name)s,%(url)s)", extracted["items"])
        cur.executemany("INSERT INTO people VALUES (%(unit_id)s,%(name)s,%(titles)s,%(function)s,%(affiliation)s,%(email)s,"
                        "%(phone)s,%(profile_url)s,%(source_url)s,%(contact)s,%(position)s)", extracted["people"])
        cur.executemany("INSERT INTO chunks VALUES (%s,%s,%s,%s,%s,%s,to_tsvector(%s::regconfig,%s),%s)",
                        [(c["id"], c["unit_id"], c["url"], c["lang"], c["text"], c["is_terms"], STEMMER[c["lang"]], c["text"], v)
                         for c, v in zip(chunks, vectors)])
        cs, labels = concepts.load(domain)
        cur.executemany("INSERT INTO concepts VALUES (%(id)s,%(source)s)", cs)
        cur.executemany("INSERT INTO concept_labels VALUES (%(concept_id)s,%(lang)s,%(label)s,%(match_key)s)", labels)
        idx = concepts.index(labels)
        cur.executemany("INSERT INTO chunk_concepts VALUES (%s,%s)",
                        [(c["id"], cid) for c in chunks for cid in concepts.tag(c["text"], idx)])
        cur.executemany("INSERT INTO report_sentences VALUES (%(section)s,%(position)s,%(sentence)s,%(url)s,%(source_sentence)s)", report)
        counts = {"pages": len(pages), "units": len(units), "chunks": len(chunks), "people": len(extracted["people"]),
                  "items": len(extracted["items"]), "concepts": len(cs), "report_sentences": len(report)}
        build_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        cur.execute("INSERT INTO build VALUES (%s,%s,%s,%s,now(),%s)", (build_id, domain.id, embed.MODEL_ID, embed.DIM, Jsonb(counts)))
    conn.execute("SET search_path TO public")
    conn.commit()
    print(f"loaded build {build_id} into staging_{domain.id}: {counts}")
    return build_id


def go_live(conn, domain: Domain):
    staging, live, previous = (sql.Identifier(f"{p}_{domain.id}") for p in ("staging", "live", "previous"))
    with conn.transaction():
        conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(previous))
        if schema_exists(conn, f"live_{domain.id}"):          # false only on the very first build
            conn.execute(sql.SQL("ALTER SCHEMA {} RENAME TO {}").format(live, previous))
        conn.execute(sql.SQL("ALTER SCHEMA {} RENAME TO {}").format(staging, live))
    print(f"live_{domain.id} is now the new build")
