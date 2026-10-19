import os

os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")

from fastapi.testclient import TestClient  # noqa: E402

from navigator.api import adjust_from, app  # noqa: E402

client = TestClient(app)   # no lifespan: only request validation runs, before any handler


def test_search_rejects_empty_need():
    for card in ({"needs": []}, {"needs": [{"id": "n1", "text": ""}]}, {"needs": [{"id": "n1", "text": "x" * 301}]},
                 {"needs": [{"id": "n1", "text": "abc"}, {"id": "n1", "text": "def"}]},
                 {"needs": [{"id": "n1", "text": "abc", "extra": 1}]}):
        r = client.post("/api/medtech/search", json={"card": card})
        assert r.status_code == 422 and r.json()["request_id"], card


def test_description_limit():
    r = client.post("/api/medtech/need-card/draft", json={"description": "word " * 4001})
    assert r.status_code == 422


def test_adjust_from_feedback():
    a = adjust_from([{"action": "more_like_this", "need_id": "n1", "unit_id": "u1"},
                     {"action": "already_in_contact", "need_id": "n1", "unit_id": "u2"},
                     {"action": "too_academic", "need_id": "n1", "unit_id": "u3"}])
    assert a.liked == {"n1": ["u1"]} and a.hidden == {"u2"} and a.category_weight["research_partner"] == 0.5
