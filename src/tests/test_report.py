import uuid
from datetime import date, datetime

import pytest

from navigator import report
from navigator.config import load_domain
from navigator.models import Lead, LeadGroup, NeedCard, Person, Reason, SearchResult

EVIL = '<img src="http://10.0.0.1/secret.png">'
PAGE = "https://www.artorg.unibe.ch/research/msl/index_eng.html"


def person(name: str, contact: bool) -> Person:
    return Person(name=name, titles="Prof. Dr.", function="Head" if contact else "Postdoc", affiliation="MSL", email=f"{name}@unibe.ch",
                  phone="+41 31 000 00 00", profile_url=None, source_url=PAGE, contact=contact, reason=None)


def result(summary: str) -> SearchResult:
    card = NeedCard(product="Glucose meter", needs=[{"id": "n1", "text": "Clinical validation of a glucose sensor"}])
    lead = Lead(unit_id="artorg-msl", name="Medical Sensing", parent="ARTORG", host="artorg.unibe.ch", category="research_partner",
                summary=summary, expertise=[], explanation=None, need_ids=["n1"], items=[], page_date=date(2025, 1, 1), stale=False,
                people=[person("lead", True), person("member", False)], url=PAGE, score=1.0, page_count=4,
                checked_at=datetime(2026, 10, 19, 10, 0),
                reasons=[Reason(need_id="n1", need_text="Clinical validation", sentence="We validate sensors.", url=PAGE, live="found"),
                         Reason(need_id="n1", need_text="Clinical validation", sentence="We ran a trial.", url=PAGE + "#old", live="changed")])
    return SearchResult(request_id=uuid.uuid4(), domain="medtech", build_id="b1", card=card, coverage_line="Covered: n1.",
                        groups=[LeadGroup(category="research_partner", label="Research partner", leads=[lead])],
                        covered=["n1"], uncovered=[])


def doc(summary: str, audience: report.Audience = "internal") -> str:
    return report.html(result(summary), {"artorg-msl": [PAGE]}, [], load_domain("medtech"), datetime(2026, 10, 19), audience)


@pytest.mark.parametrize("audience", ["internal", "external"])
def test_report_escapes_and_blocks_urls(audience):
    html = doc(f"Builds sensors. {EVIL}", audience)
    assert EVIL not in html and "&lt;img" in html
    assert report.pdf(html)[:4] == b"%PDF"
    from weasyprint.urls import FatalURLFetchingError
    with pytest.raises(FatalURLFetchingError):
        report.pdf(html.replace("</body>", f"{EVIL}</body>"))


def test_internal_shows_everything_for_review():
    html = doc("Builds sensors.")
    assert "lead@unibe.ch" in html and "member@unibe.ch" in html
    assert "We ran a trial." in html and "no longer on the page" in html


def test_external_names_contact_persons_only_and_drops_changed_quotes():
    html = doc("Builds sensors.", "external")
    assert "@unibe.ch" not in html and "+41" not in html
    assert "lead" in html and "member" not in html
    assert "We validate sensors." in html and "We ran a trial." not in html


def test_every_sentence_needs_a_source():
    with pytest.raises(AssertionError, match="without a source"):
        report.Notes()("A sentence.", "")


def test_rejected_leads_stay_out_of_the_company_report():
    res = result("Builds sensors.")
    args = (res, {"artorg-msl": [PAGE]}, [], load_domain("medtech"), datetime(2026, 10, 19))
    assert "Medical Sensing" not in report.html(*args, "external", {"artorg-msl"})
    assert "Marked not relevant" in report.html(*args, "internal", {"artorg-msl"})
