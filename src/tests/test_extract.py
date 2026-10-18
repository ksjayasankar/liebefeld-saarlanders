import pytest

from navigator import concepts
from navigator.config import load_domain
from navigator.extract import collect_people, page_type, parse_html, split_name
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


LIST = """<html><head><meta name="DC.Date" content="01.01.2026"></head><body><main id="content"><h1>Group Members</h1>
<h2>Group Head</h2><article class="team-box" itemscope itemtype="http://schema.org/Person"><dl class="left">
<dt class="sr-only">Name / Titel</dt><dd><a href="persons/prof_dr_b_a/index_eng.html">Prof. Dr. A B</a></dd>
<dt class="sr-only">Funktion</dt><dd class="jobTitle">Group Head</dd>
<dt class="sr-only">Mail</dt><dd class="mail"><a href="javascript:void(0)" itemprop="email">a.b@unibe.ch</a></dd></dl>
<dl class="right"><dt>Phone</dt><dd itemprop="telephone"><a href="tel:+41 31 684 14 89">+41 31 684 14 89</a></dd></dl></article>
<article class="team-box" itemscope itemtype="http://schema.org/Person"><dl class="left">
<dt class="sr-only">Name / Titel</dt><dd> C D</dd><dt class="sr-only">Funktion</dt><dd class="jobTitle">PhD Student</dd></dl></article>
<h2>Alumni</h2><article class="team-box" itemscope itemtype="http://schema.org/Person"><dl class="left">
<dt class="sr-only">Name / Titel</dt><dd>Old Member</dd></dl></article></main></body></html>"""
PROFILE = """<html><head><meta name="DC.Date" content="01.01.2026"></head><body><main id="content">
<article class="team-detail" itemscope itemtype="http://schema.org/Person"><h1 itemprop="name">Prof. Dr. A B</h1>
<p itemprop="jobTitle">Group Head</p><p>University of Bern, ARTORG Center</p>
<dl><dt>E-Mail</dt><dd><a itemprop="email">a.b@unibe.ch</a></dd></dl></article>
<p>Her group develops glucose sensors and runs clinical studies with the university hospital in Bern.</p></main></body></html>"""
BASE = "https://www.artorg.unibe.ch/research/aihn/group_members/"


def test_person_markup_on_member_list_and_own_page():
    lst = parse_html(D, "artorg.unibe.ch", BASE + "index_eng.html", LIST)
    assert [(e["name"], e["function"], e["email"], e["phone"]) for e in lst.people] == [
        ("Prof. Dr. A B", "Group Head", "a.b@unibe.ch", "+41 31 684 14 89"), ("C D", "PhD Student", None, None)]
    assert lst.people[0]["profile_url"] == BASE + "persons/prof_dr_b_a/index_eng.html" and not lst.people[0]["own_page"]
    own = parse_html(D, "artorg.unibe.ch", BASE + "persons/prof_dr_b_a/index_eng.html", PROFILE)
    assert own.people[0]["own_page"] and own.people[0]["affiliation"] == "University of Bern, ARTORG Center"
    assert "@" not in own.text


def test_collect_people_merges_own_page_into_list_entry():
    lst = parse_html(D, "artorg.unibe.ch", BASE + "index_eng.html", LIST)
    own = parse_html(D, "artorg.unibe.ch", BASE + "persons/prof_dr_b_a/index_eng.html", PROFILE)
    lst.unit_id, own.unit_id = "artorg-aihn", "artorg"
    rows = collect_people([own, lst], {"artorg-aihn": "AIHN", "artorg": "ARTORG"}, {own.url, lst.url})
    assert [(r["unit_id"], r["name"], r["titles"], r["affiliation"], r["contact"]) for r in rows] == [
        ("artorg-aihn", "A B", "Prof. Dr.", "University of Bern, ARTORG Center", True), ("artorg-aihn", "C D", "", "AIHN", False)]
    assert [r["position"] for r in rows] == [0, 1]
    assert rows[0]["profile_url"] == own.url and rows[0]["source_url"] == lst.url


def test_profile_link_kept_only_when_fetched():
    lst = parse_html(D, "artorg.unibe.ch", BASE + "index_eng.html", LIST)
    lst.unit_id = "artorg-aihn"
    assert collect_people([lst], {"artorg-aihn": "AIHN"}, {lst.url})[0]["profile_url"] is None


def test_concept_tag_longest_first():
    idx = concepts.index([{"concept_id": "cgm", "match_key": "continuous glucose monitoring"},
                          {"concept_id": "glucose", "match_key": "glucose"}])
    assert concepts.tag("Continuous glucose-monitoring for kids", idx) == {"cgm"}
    assert concepts.tag("Glucose and continuous glucose monitoring", idx) == {"cgm", "glucose"}
