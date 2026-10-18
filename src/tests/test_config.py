import pytest
import yaml

from navigator import config


def _write(tmp_path, monkeypatch, **changes):
    pack = yaml.safe_load((config.ROOT / "config/domains/medtech.yaml").read_text())
    for path, value in changes.items():
        node = pack
        *head, last = path.split(".")
        for k in head:
            node = node[int(k)] if k.isdigit() else node[k]
        node[last] = value
    (tmp_path / "config/domains").mkdir(parents=True)
    (tmp_path / "eval").mkdir()
    (tmp_path / "config/domains" / f"{pack['id']}.yaml").write_text(yaml.safe_dump(pack))
    monkeypatch.setattr(config, "ROOT", tmp_path)
    return pack["id"]


def test_real_pack_loads():
    d = config.load_domain("medtech")
    assert d.host("artorg.unibe.ch").priority == 1


@pytest.mark.parametrize("change", [
    {"id": "MedTech"},
    {"hosts.0.template": "nope"},
    {"templates.unibe_portal.main": "<css selector>"},
    {"templates.unibe_portal.drop": [""]},
    {"vocabularies": ["vocab/missing.json"]},
    {"hosts.0.render": "browser"},
])
def test_load_domain_asserts(tmp_path, monkeypatch, change):
    domain_id = _write(tmp_path, monkeypatch, **change)
    with pytest.raises(AssertionError):
        config.load_domain(domain_id)
