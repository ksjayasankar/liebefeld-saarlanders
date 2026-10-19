"""`navigator index` runs the build steps in order; each step also runs on its own and reads the previous step's file."""
import json

from . import db
from .config import ROOT, load_domain


def _path(domain_id: str, step: str):
    return ROOT / "data/build" / domain_id / f"{step}.json"


def _save(domain_id: str, step: str, data):
    path = _path(domain_id, step)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False))


def _load(domain_id: str, step: str):
    return json.loads(_path(domain_id, step).read_text())


def extract(domain_id: str):
    from . import extract as m
    with db.connect() as conn:
        _save(domain_id, "extract", m.run(conn, load_domain(domain_id)))


def enrich(domain_id: str):
    from . import enrich as m
    _save(domain_id, "enrich", m.run(_load(domain_id, "extract")))


def embed(domain_id: str):
    from . import embed as m
    from .load import chunk_rows
    with db.connect() as conn:
        m.cached(conn, [c["text"] for c in chunk_rows(_load(domain_id, "extract"), _load(domain_id, "enrich"))])


def report(domain_id: str):
    from . import report_sections as m
    with db.connect() as conn:
        _save(domain_id, "report", m.run(conn, load_domain(domain_id), _load(domain_id, "extract")["pages"]))


def load(domain_id: str):
    from . import load as m
    with db.connect() as conn:
        m.build(conn, load_domain(domain_id), _load(domain_id, "extract"), _load(domain_id, "enrich"), _load(domain_id, "report"))


def check(domain_id: str):
    from . import checks, load as m
    with db.connect() as conn:
        checks.run(conn, load_domain(domain_id), f"staging_{domain_id}")
        m.go_live(conn, load_domain(domain_id))


def index(domain_id: str):
    for step in (extract, enrich, embed, report, load, check):
        print(f"== {step.__name__}", flush=True)
        step(domain_id)
