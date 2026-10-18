"""Loads and asserts the domain pack and the environment. No defaults for settings."""
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = ("research_partner", "facility", "clinical_validation", "licensing", "support", "talent")
STAGES = ("idea", "prototype", "clinical_testing", "on_market")
LANGS = ("en", "de", "fr")


def env(name: str) -> str:
    return os.environ[name]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Template(Strict):
    main: str | None = None          # CSS selector of the content area (HTML templates)
    drop: list[str] = []             # selectors removed inside the content area
    alumni_headings: list[str] = []  # text after one of these headings is cut
    wp_api: str | None = None        # WordPress REST base path (DCB)
    unit_paths: list[str] = []       # regexes on the URL path whose first group is a unit code


class Host(Strict):
    url: str
    template: str
    priority: int
    role: str | None = None          # location_facts: report source only, no units
    render: str | None = None

    @property
    def name(self) -> str:
        return urlsplit(self.url).netloc.lower().removeprefix("www.")


class Domain(Strict):
    id: str
    label: str
    languages: list[str]
    max_pages_per_host: int
    templates: dict[str, Template]
    hosts: list[Host]
    vocabularies: list[str]
    report_sections: list[str]
    report_sources: list[str]
    test_set: str

    def host(self, name: str) -> Host:
        (h,) = [h for h in self.hosts if h.name == name]
        return h


def load_domain(domain_id: str) -> Domain:
    d = Domain(**yaml.safe_load((ROOT / "config/domains" / f"{domain_id}.yaml").read_text()))
    assert re.fullmatch(r"[a-z]+", d.id) and d.id == domain_id, f"bad domain id {d.id!r}"
    assert set(d.languages) <= set(LANGS), d.languages
    for name, t in d.templates.items():
        assert (t.main is None) != (t.wp_api is None), f"template {name}: exactly one of main and wp_api"
        for sel in [t.main, *t.drop] if t.main else t.drop:
            assert sel.strip() and "<" not in sel, f"template {name}: empty or placeholder selector"
    for h in d.hosts:
        assert h.template in d.templates, f"host {h.url}: unknown template {h.template}"
        assert h.url.startswith("https://") and h.url.endswith("/"), f"host url {h.url}"
        assert h.render is None, f"host {h.url}: render={h.render} needs Playwright, not installed (decision D-09)"
    assert len({h.name for h in d.hosts}) == len(d.hosts), "duplicate host"
    for p in [*d.vocabularies, d.test_set]:
        assert (ROOT / p).exists(), f"missing path {p}"
    hosts = {h.name for h in d.hosts}
    for u in d.report_sources:
        assert urlsplit(u).netloc.lower().removeprefix("www.") in hosts, f"report source {u} not on a domain host"
    return d


def load_yaml(name: str):
    return yaml.safe_load((ROOT / "config" / name).read_text())
