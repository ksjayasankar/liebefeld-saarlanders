"""Spec 5.6: BGE-M3 vectors and the bge-reranker-v2-m3 scores. One module for build and search."""
import hashlib
from functools import cache

import numpy as np
import torch

from .config import env
from .normalise import sentences, words

EMBEDDER = ("BAAI/bge-m3", "5617a9f61b028005a4858fdac845db406aefb181")
RERANKER = ("BAAI/bge-reranker-v2-m3", "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e")
MODEL_ID = "@".join(EMBEDDER)
DIM = 1024
CHUNK_MIN, CHUNK_MAX = 200, 350


@cache
def embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDER[0], revision=EMBEDDER[1], device=env("TORCH_DEVICE"))


@cache
def reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(RERANKER[0], revision=RERANKER[1], device=env("TORCH_DEVICE"), max_length=512)


def encode(texts: list[str]) -> np.ndarray:
    v = embedder().encode(texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
    assert v.shape == (len(texts), DIM) and np.allclose(np.linalg.norm(v, axis=1), 1, atol=1e-3)
    return v


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def cached(conn, texts: list[str], batch: int = 512) -> np.ndarray:
    """Vectors from cache.embeddings; only unseen texts are encoded, in batches that are committed as they finish."""
    hashes = [text_hash(t) for t in texts]
    have = {r["text_hash"]: r["embedding"] for r in conn.execute(
        "SELECT text_hash, embedding FROM cache.embeddings WHERE model_id = %s AND text_hash = ANY(%s)", (MODEL_ID, hashes))}
    todo = list({h: t for h, t in zip(hashes, texts) if h not in have}.items())
    for i in range(0, len(todo), batch):
        part = todo[i:i + batch]
        for (h, _), v in zip(part, encode([t for _, t in part])):
            conn.execute("INSERT INTO cache.embeddings VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (MODEL_ID, h, v))
            have[h] = v
        conn.commit()
        print(f"embedded {min(i + batch, len(todo))}/{len(todo)} new texts", flush=True)
    return np.stack([np.asarray(have[h], dtype=np.float32) for h in hashes]) if texts else np.zeros((0, DIM), np.float32)


def rerank(query: str, texts: list[str]) -> np.ndarray:
    scores = reranker().predict([(query, t) for t in texts], batch_size=16, activation_fn=torch.nn.Sigmoid(), convert_to_numpy=True)
    return np.asarray(scores, dtype=np.float32)


def chunk(title: str, text: str) -> list[str]:
    """Chunks of at most 350 words split at paragraphs (long paragraphs at sentences), page title in front.
    A short tail joins the previous chunk when the result stays within the limit."""
    pieces = [s for para in text.split("\n") if para.strip()
              for s in (sentences(para) or [para] if words(para) > CHUNK_MAX else [para])]
    chunks, cur = [], []
    for piece in pieces:
        if cur and words(" ".join(cur + [piece])) > CHUNK_MAX:
            chunks.append(cur)
            cur = []
        cur.append(piece)
    if cur:
        if chunks and words(" ".join(cur)) < CHUNK_MIN and words(" ".join(chunks[-1] + cur)) <= CHUNK_MAX:
            chunks[-1] += cur
        else:
            chunks.append(cur)
    return [f"{title}\n" + "\n".join(c) for c in chunks]
