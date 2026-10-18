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
    strip_patterns: list[str] = []   # regexes removed from the text (page-builder shortcodes)
    skip_without: str | None = None  # pages where this selector matches nothing are navigation pages without content
    alumni_headings: list[str] = []  # text after one of these headings is cut
    wp_api: str | None = None        # WordPress REST base path (DCB)
    wp_types: list[str] = []         # WordPress post types fetched through wp_api
    unit_paths: list[str] = []       # regexes on the URL path whose first group is a unit code
    page_types: dict[str, str] = {}  # page type -> regex on the URL path (HTML) or post type (WordPress); first match wins


class Host(Strict):
    label: str                       # name of the host's own unit (its institute or centre)
    url: str
    template: str
    priority: int
    unit_paths: list[str] | None = None  # replaces the template's unit_paths for this host
    role: str | None = None          # news: the host's pages are evidence of other units' work, the host is never a lead
    render: str | None = None

    @property
    def name(self) -> str:
        return urlsplit(self.url).netloc.lower().removeprefix("www.")


class ReportSection(Strict):
    title: str
    brief: str                       # what the section tells a company, given to Apertus
    sources: list[str]               # public pages the section is written from


class Domain(Strict):
    id: str
    label: str
    languages: list[str]
    max_pages_per_host: int
    templates: dict[str, Template]
    hosts: list[Host]
    vocabularies: list[str]
    coverage_threshold: float        # best reranker score below which a need counts as uncovered (tuned on the answer key)
    report_sections: dict[str, ReportSection]
    report_banned: list[str]         # promotional words, comparisons, other cantons and cities
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
        assert list(t.page_types.values())[-1:] == [".*"], f"template {name}: last page type must be the catch-all '.*'"
        for sel in [t.main, *t.drop] if t.main else t.drop:
            assert sel.strip() and "<" not in sel, f"template {name}: empty or placeholder selector"
    for h in d.hosts:
        assert h.template in d.templates, f"host {h.url}: unknown template {h.template}"
        assert h.url.startswith("https://") and h.url.endswith("/"), f"host url {h.url}"
        assert h.role in (None, "news"), f"host {h.url}: unknown role {h.role}"
        assert h.render is None, f"host {h.url}: render={h.render} needs Playwright, not installed (decision D-09)"
    assert len({h.name for h in d.hosts}) == len(d.hosts), "duplicate host"
    for p in [*d.vocabularies, d.test_set]:
        assert (ROOT / p).exists(), f"missing path {p}"
    hosts = {h.name for h in d.hosts}
    for name, sec in d.report_sections.items():
        assert sec.sources, f"report section {name} has no sources"
        for u in sec.sources:
            assert urlsplit(u).netloc.lower().removeprefix("www.") in hosts, f"report source {u} not on a domain host"
    return d


def load_yaml(name: str):
    return yaml.safe_load((ROOT / "config" / name).read_text())
