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
