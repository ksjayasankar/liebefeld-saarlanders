"""Request and response types shared by rank.py, api.py, eval.py and report.py (decision D-06)."""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from .config import Strict

Category = Literal["research_partner", "facility", "clinical_validation", "licensing", "support", "talent"]
Stage = Literal["idea", "prototype", "clinical_testing", "on_market"]
CATEGORY_LABELS = {  # display order of lead groups (spec 6.4)
    "research_partner": "Research partner",
    "facility": "Facility or lab service",
    "clinical_validation": "Clinical and regulatory validation",
    "support": "Funding or support",
    "licensing": "Licensing",
    "talent": "Talent",
}
Action = Literal["more_like_this", "not_relevant", "wrong_topic", "too_academic", "outdated", "wrong_stage", "already_in_contact"]


class Need(Strict):
    id: str = Field(pattern=r"^n[1-5]$")
    text: str = Field(min_length=3, max_length=300)
    category: Category | None = None


class NeedCard(Strict):
    sector: str | None = Field(default=None, max_length=100)
    product: str | None = Field(default=None, max_length=200)
    stage: Stage | None = None
    needs: list[Need] = Field(min_length=1, max_length=5)

    @field_validator("needs")
    @classmethod
    def unique_ids(cls, needs):
        assert len({n.id for n in needs}) == len(needs), "need ids must be unique"
        return needs


class DraftRequest(Strict):
    description: str = Field(min_length=20, max_length=20000)


class PdfText(Strict):
    text: str                             # shown to staff for review; only what they then submit reaches Apertus
    pages: int


class Draft(Strict):
    card: NeedCard
    sentences: list[str]                  # the numbered description sentences the needs cite
    sources: dict[str, list[int]]         # need id -> sentence numbers
    ignored: list[str]                    # description sentences addressed to an AI system, not sent to the model


class SearchRequest(Strict):
    card: NeedCard


class Reason(Strict):
    need_id: str
    need_text: str
    sentence: str                         # quoted from the unit's own page
    url: str
    live: Literal["found", "changed", "gone", "unreachable", "not_checked"] | None = None   # page fetched again at search time (D-32)


class Item(Strict):
    kind: Literal["project", "facility"]
    name: str
    url: str


class Person(Strict):
    name: str
    titles: str                           # "Prof. Dr.", as written on the page
    function: str | None                  # job title as written on the page
    affiliation: str                      # the unit, or the line under the name on the person's own page
    email: str | None
    phone: str | None
    profile_url: str | None               # the person's own page, when the site has one
    source_url: str                       # the page this entry is read from
    contact: bool                         # leads the unit (head, director, PI): the person to approach first
    reason: Reason | None                 # quoted from the person's own page, when it matches a need


class Lead(Strict):
    unit_id: str
    name: str
    parent: str | None
    host: str
    category: Category
    summary: str
    expertise: list[str]                  # the unit's terms (English), from its own pages
    explanation: str | None               # one sentence on why the lead matches, supported by the quoted reasons
    need_ids: list[str]
    reasons: list[Reason]
    items: list[Item]                     # projects and facilities
    people: list[Person]                  # contact persons first, then people whose own page matches a need
    page_date: date | None
    stale: bool                           # page older than three years
    url: str
    score: float
    page_count: int
    checked_at: datetime | None = None    # when the quoted pages were fetched again (D-32)


class LeadGroup(Strict):
    category: Category
    label: str
    leads: list[Lead]


class SearchResult(Strict):
    request_id: UUID
    domain: str
    build_id: str
    card: NeedCard
    groups: list[LeadGroup]
    covered: list[str]                    # need ids with at least one lead above the threshold
    uncovered: list[str]
    coverage_line: str
    message: str | None = None            # what the last feedback changed


class FeedbackRequest(Strict):
    unit_id: str
    need_id: str
    action: Action


class IntroductionRequest(Strict):
    unit_ids: list[str] = Field(min_length=1, max_length=10)
    message: str = Field(max_length=2000)


class Introduction(Strict):
    id: UUID
    request_id: UUID
    card: NeedCard
    leads: list[Lead]
    feedback: list[FeedbackRequest]
    message: str
    status: str
    created_at: datetime


class Health(Strict):
    domains: dict[str, dict]              # domain -> build id, counts, model id
    models: dict[str, str]
