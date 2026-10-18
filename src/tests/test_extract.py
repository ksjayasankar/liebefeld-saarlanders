import pytest

from navigator import concepts
from navigator.config import load_domain
from navigator.extract import member_rows, page_type, parse_html, split_name
from navigator.normalise import clean_text, match_key, sentences

D = load_domain("medtech")
PAGE = """<html><head><meta name="DC.Date" content="22.12.2025"></head><body><main id="content">
<h1>Medical Sensing</h1><aside class="contact-box">Contact jane@unibe.ch</aside>
<p>We build <a href="#">continuous glucose</a> sensors. Call +41 31 684 14 89 or mail a.b@unibe.ch today.</p>
<h2>Alumni</h2><p>Old Member was here for years and years.</p></main></body></html>"""


def test_match_key_folds_accents_and_hyphens():
    assert match_key("García-López") == match_key("garcia lopez") == "garcia lopez"
    assert match_key("Children’s  Hospital") == "children s hospital"


def test_clean_text_removes_contacts_and_invisible():
    assert clean_text("Call +41 31 684 14 89 or 031 684 14 89, mail x.y@unibe.ch.­ ok") == "Call or , mail . ok"
    assert clean_text("ﬁnd   it\n\n\n\nnext") == "find it\n\nnext"


def test_sentences_split():
    assert sentences("One two three. Four five six!\nSeven eight nine") == ["One two three.", "Four five six!", "Seven eight nine"]


def test_parse_html_cleans_and_cuts_alumni():
    p = parse_html(D, "artorg.unibe.ch", "https://www.artorg.unibe.ch/research/msl/index_eng.html", PAGE)
    assert (p.title, p.lang, p.page_date) == ("Medical Sensing", "en", "2025-12-22")
    assert "continuous glucose sensors" in p.text and "@" not in p.text and "Contact" not in p.text
    assert "Old Member" not in p.text


def test_main_content_requires_single_match():
    with pytest.raises(AssertionError, match="2 matches"):
        parse_html(D, "artorg.unibe.ch", "https://www.artorg.unibe.ch/x/index_eng.html",
                   PAGE.replace("</main>", "</main><main id='content'></main>"))


def test_page_type_rules():
    t = D.templates["unibe_portal"]
    assert page_type(t, "/research/aihn/group_members/index_eng.html") == "members"
    assert page_type(t, "/research/aihn/group_members/persons/dr_x/index_eng.html") == "person"
    assert page_type(t, "/services/3d_printing/index_eng.html") == "facility"
    assert page_type(t, "/research/aihn/research_activities/x/index_eng.html") == "project"
    assert page_type(t, "/about_us/index_eng.html") == "other"


def test_unibe_name_order():
    assert split_name("Muster, Hans, Prof. Dr.") == ("Hans Muster", "Prof. Dr.")
    assert split_name("Prof. em. Dr. Diem, Peter") == ("Peter Diem", "Prof. em. Dr.")
    assert split_name("Dr. med. Anna Beispiel") == ("Anna Beispiel", "Dr. med.")


def test_member_rows():
    raw = "Group Head\nName / Titel\nProf. Dr. A B\nFunktion\nGroup Head\nMail\nName / Titel\nC D\nMail\n"
    assert member_rows(raw) == [("Prof. Dr. A B", "Group Head"), ("C D", "")]


def test_concept_tag_longest_first():
    idx = concepts.index([{"concept_id": "cgm", "match_key": "continuous glucose monitoring"},
                          {"concept_id": "glucose", "match_key": "glucose"}])
    assert concepts.tag("Continuous glucose-monitoring for kids", idx) == {"cgm"}
    assert concepts.tag("Glucose and continuous glucose monitoring", idx) == {"cgm", "glucose"}
