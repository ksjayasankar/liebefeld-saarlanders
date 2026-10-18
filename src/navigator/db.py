"""Connections and migrations."""
import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import ROOT, env

MIGRATIONS = sorted((ROOT / "migrations").glob("*.sql"))


def connect() -> psycopg.Connection:
    conn = psycopg.connect(env("DATABASE_URL"), row_factory=dict_row)
    register_vector(conn)
    return conn


def pool() -> ConnectionPool:
    return ConnectionPool(env("DATABASE_URL"), kwargs={"row_factory": dict_row}, configure=register_vector, open=True)


def schema_exists(conn, name: str) -> bool:
    return conn.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", (name,)).fetchone() is not None


def version(conn) -> int:
    return conn.execute("SELECT version FROM app.schema_version").fetchone()["version"] if schema_exists(conn, "app") else 0


def migrate() -> int:
    with psycopg.connect(env("DATABASE_URL"), row_factory=dict_row) as conn:
        for path in MIGRATIONS[version(conn):]:
            n = int(path.name.split("_")[0])
            assert n == version(conn) + 1, f"migration numbering gap at {path.name}"
            conn.execute(path.read_text())
            conn.execute("UPDATE app.schema_version SET version = %s", (n,))
            conn.commit()
        return version(conn)


def latest_version() -> int:
    return len(MIGRATIONS)
