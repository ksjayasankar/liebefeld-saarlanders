"""Export and import of the dataset and the caches as Parquet, so only one person fetches (spec 5)."""
import shutil
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from . import db
from .config import ROOT

TABLES = {"dataset.pages": "url", "cache.model_calls": "key", "cache.embeddings": "model_id, text_hash"}


def export(path: str):
    out = Path(path)
    out.mkdir(parents=True, exist_ok=False)
    with db.connect() as conn:
        for table in TABLES:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            for r in rows:
                for k, v in r.items():
                    r[k] = v.tolist() if isinstance(v, np.ndarray) else str(v) if k == "answer" else v
            pq.write_table(pa.Table.from_pylist(rows), out / f"{table}.parquet")
            print(table, len(rows))
    shutil.copytree(ROOT / "data/raw", out / "raw")


def import_(path: str):
    src = Path(path)
    with db.connect() as conn:
        for table, key in TABLES.items():
            rows = pq.read_table(src / f"{table}.parquet").to_pylist()
            cols = list(rows[0]) if rows else []
            for r in rows:
                conn.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) "
                             f"ON CONFLICT ({key}) DO NOTHING",
                             [np.array(r[c]) if c == "embedding" else r[c] for c in cols])
            print(table, len(rows))
        conn.commit()
    shutil.copytree(src / "raw", ROOT / "data/raw", dirs_exist_ok=True)
