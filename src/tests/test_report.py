import uuid
from datetime import date, datetime

import pytest

from navigator import report
from navigator.config import load_domain
from navigator.models import Lead, LeadGroup, NeedCard, Reason, SearchResult

EVIL = '<img src="http://10.0.0.1/secret.png">'


def result(summary: str) -> SearchResult:
    card = NeedCard(product="Glucose meter", needs=[{"id": "n1", "text": "Clinical validation of a glucose sensor"}])
    lead = Lead(unit_id="artorg-msl", name="Medical Sensing", parent="ARTORG", host="artorg.unibe.ch", category="research_partner",
                summary=summary, need_ids=["n1"], items=[], people=[], page_date=date(2025, 1, 1), stale=False,
                url="https://www.artorg.unibe.ch/research/msl/index_eng.html", score=1.0, page_count=4,
                reasons=[Reason(need_id="n1", need_text="Clinical validation", sentence="We validate sensors.",
                                url="https://www.artorg.unibe.ch/research/msl/index_eng.html")])
    return SearchResult(request_id=uuid.uuid4(), domain="medtech", build_id="b1", card=card, coverage_line="Covered: n1.",
                        groups=[LeadGroup(category="research_partner", label="Research partner", leads=[lead])],
                        covered=["n1"], uncovered=[])


def doc(summary: str) -> str:
    return report.html(result(summary), {"artorg-msl": ["https://www.artorg.unibe.ch/research/msl/index_eng.html"]}, [],
                       load_domain("medtech"), datetime(2026, 10, 19))


def test_report_escapes_and_blocks_urls():
    html = doc(f"Builds sensors. {EVIL}")
    assert EVIL not in html and "&lt;img" in html
    assert report.pdf(html)[:4] == b"%PDF"
    from weasyprint.urls import FatalURLFetchingError
    with pytest.raises(FatalURLFetchingError):
        report.pdf(html.replace("</body>", f"{EVIL}</body>"))


def test_every_sentence_needs_a_source():
    with pytest.raises(AssertionError, match="without a source"):
        report.Notes()("A sentence.", "")
