"""Spec 6.1: stateless FastAPI app. Everything lives in Postgres; the browser only displays what this returns."""
import json
import queue
import threading
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from typing import Annotated

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from psycopg import sql
from psycopg.types.json import Jsonb

from . import apertus, db, embed, explain, live, needcard, pdf, rank
from .config import env, load_domain
from .models import (Draft, DraftRequest, FeedbackRequest, Health, Introduction, IntroductionRequest, NeedCard, PdfText,
                     SearchRequest, SearchResult)
from .normalise import AI_ADDRESSED, sentences

MESSAGES = {
    "more_like_this": "Leads closer to this one are now ranked higher for this need.",
    "not_relevant": "Leads like this one are now ranked lower for this need.",
    "wrong_topic": "Leads like this one are now ranked lower for this need.",
    "too_academic": "Research groups are ranked lower; facilities and support programmes higher.",
    "outdated": "Leads whose evidence is older than three years are hidden.",
    "wrong_stage": "Clinical and regulatory validation leads are ranked higher.",
    "already_in_contact": "This lead is hidden and noted for the agency.",
}
STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Spec section 3: the API does not start unless every assert holds."""
    domains = {d: load_domain(d) for d in env("DOMAINS").split(",")}
    pool = db.pool()
    with pool.connection() as conn:
        assert db.version(conn) == db.latest_version(), "database is not at the latest migration"
        for d in domains:
            assert db.schema_exists(conn, f"live_{d}"), f"live_{d} does not exist; run navigator index --domain {d}"
            b = conn.execute(sql.SQL("SELECT * FROM {}.build").format(sql.Identifier(f"live_{d}"))).fetchone()
            assert (b["model_id"], b["dim"]) == (embed.MODEL_ID, embed.DIM), f"live_{d} was built with {b['model_id']}"
    listed = {m.id for m in apertus._client().models.list().data}
    assert {env("APERTUS_8B"), env("APERTUS_70B")} <= listed, f"gateway does not list the configured models: {listed}"
    embed.embedder(), embed.reranker(), pdf.converter()
    STATE.update(domains=domains, pool=pool, hits=defaultdict(deque))
    yield
    pool.close()


app = FastAPI(title="Research & Expertise Navigator", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=env("CORS_ORIGINS").split(","), allow_methods=["GET", "POST"], allow_headers=["*"])


@app.middleware("http")
async def request_id(request: Request, call_next):
    request.state.id = uuid.uuid4().hex[:12]
    try:
        response = await call_next(request)
    except Exception as e:   # shown on screen as it is, with the request id (spec 6.7)
        print(f"[{request.state.id}] {type(e).__name__}: {e}", flush=True)
        response = JSONResponse({"detail": f"{type(e).__name__}: {e}", "request_id": request.state.id}, status_code=500)
    response.headers["X-Request-Id"] = request.state.id
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, e: HTTPException):
    return JSONResponse({"detail": e.detail, "request_id": request.state.id}, status_code=e.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, e: RequestValidationError):
    return JSONResponse({"detail": json.loads(json.dumps(e.errors(), default=str)), "request_id": request.state.id}, status_code=422)


def limit(request: Request):
    """Per-address rate limit on endpoints that call Apertus."""
    window, hits = 60.0, STATE["hits"][request.client.host]
    while hits and hits[0] < time.time() - window:
        hits.popleft()
    if len(hits) >= int(env("RATE_LIMIT_PER_MINUTE")):
        raise HTTPException(429, "rate limit reached; try again in a minute")
    hits.append(time.time())


def domain_of(name: str):
    if name not in STATE["domains"]:
        raise HTTPException(404, f"unknown domain {name}")
    return STATE["domains"][name]


def stored(conn, request_id: uuid.UUID) -> dict:
    row = conn.execute("SELECT * FROM app.requests WHERE id = %s", (request_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"unknown request {request_id}")
    return row


def result(conn, row: dict, adjust: rank.Adjust | None, message: str | None, progress=lambda event: None) -> SearchResult:
    card = NeedCard(**row["need_card"])
    r = rank.rank(conn, STATE["domains"][row["domain"]], card, adjust, progress)
    with ThreadPoolExecutor(1) as ex:   # the live check (D-32) runs while Apertus writes the explanations
        checked = ex.submit(live.check, STATE["domains"][row["domain"]], r.leads, progress)
        explain.explain_all(conn, r.leads, progress)
        checked.result()
    out = SearchResult(request_id=row["id"], domain=row["domain"], build_id=row["build_id"], card=card, groups=r.groups,
                       covered=r.covered, uncovered=r.uncovered, coverage_line=r.coverage_line, message=message)
    conn.execute("UPDATE app.requests SET leads = %s WHERE id = %s", (Jsonb(out.model_dump(mode="json")), row["id"]))
    return out


def build_id(conn, domain: str) -> str:
    return conn.execute(sql.SQL("SELECT id FROM {}.build").format(sql.Identifier(f"live_{domain}"))).fetchone()["id"]


@app.post("/api/{domain}/need-card/draft", response_model=Draft)
def draft(domain: str, body: DraftRequest, request: Request):
    domain_of(domain)
    limit(request)
    if not [s for s in sentences(body.description) if not AI_ADDRESSED.search(s)]:
        raise HTTPException(422, "the description has no full sentences about the company")
    with STATE["pool"].connection() as conn:
        return needcard.draft(conn, body.description)


@app.post("/api/{domain}/need-card/pdf", response_model=PdfText)
def pdf_text(domain: str, data: Annotated[bytes, Body(media_type="application/pdf")], request: Request):
    """D-29: the PDF is read locally and never stored; staff edit the returned text before drafting."""
    domain_of(domain)
    limit(request)
    try:
        text, pages = pdf.text(data)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return PdfText(text=text, pages=pages)


@app.post("/api/{domain}/search", response_model=SearchResult)
def search(domain: str, body: SearchRequest, request: Request):
    domain_of(domain)
    limit(request)
    with STATE["pool"].connection() as conn:
        return result(conn, new_request(conn, domain, body.card), None, None)


@app.post("/api/{domain}/search/stream")
def search_stream(domain: str, body: SearchRequest, request: Request):
    """D-30: the same search as NDJSON, one line per step ({"step": "expand"|"retrieve"|"rerank"|"select"|"explain"|"verify", ...}),
    then {"step": "result", "result": SearchResult} or {"step": "error", "detail": ...}."""
    domain_of(domain)
    limit(request)
    events: queue.Queue = queue.Queue()

    def work():
        try:
            with STATE["pool"].connection() as conn:
                out = result(conn, new_request(conn, domain, body.card), None, None, events.put)
            events.put({"step": "result", "result": out.model_dump(mode="json")})
        except Exception as e:   # reported in the stream as it is, like the error middleware does
            print(f"[{request.state.id}] {type(e).__name__}: {e}", flush=True)
            events.put({"step": "error", "detail": f"{type(e).__name__}: {e}", "request_id": request.state.id})

    def lines():
        while True:
            e = events.get()
            yield json.dumps(e) + "\n"
            if e["step"] in ("result", "error"):
                return

    threading.Thread(target=work, daemon=True).start()
    return StreamingResponse(lines(), media_type="application/x-ndjson")


def new_request(conn, domain: str, card: NeedCard) -> dict:
    return conn.execute("INSERT INTO app.requests VALUES (%s,%s,%s,%s,'{}',%s) RETURNING *",
                        (uuid.uuid4(), domain, build_id(conn, domain), Jsonb(card.model_dump(mode="json")),
                         datetime.now(timezone.utc))).fetchone()


def adjust_from(feedback: list[dict]) -> rank.Adjust:
    a = rank.Adjust()
    for f in feedback:
        act, need, unit = f["action"], f["need_id"], f["unit_id"]
        if act == "more_like_this":
            a.liked.setdefault(need, []).append(unit)
        elif act in ("not_relevant", "wrong_topic"):
            a.rejected.setdefault(need, []).append(unit)
        elif act == "too_academic":
            a.category_weight.update(research_partner=0.5, facility=1.5, support=1.5)
        elif act == "outdated":
            a.hide_stale = True
        elif act == "wrong_stage":
            a.category_weight["clinical_validation"] = 1.5
        else:
            assert act == "already_in_contact", act
            a.hidden.add(unit)
    return a


@app.post("/api/requests/{request_id}/feedback", response_model=SearchResult)
def feedback(request_id: uuid.UUID, body: FeedbackRequest, request: Request):
    limit(request)
    with STATE["pool"].connection() as conn:
        row = stored(conn, request_id)
        conn.execute("INSERT INTO app.feedback VALUES (%s,%s,%s,%s,%s,%s)",
                     (request_id, body.unit_id, body.need_id, body.action, None, datetime.now(timezone.utc)))
        rows = conn.execute("SELECT unit_id, need_id, action FROM app.feedback WHERE request_id = %s ORDER BY created_at",
                            (request_id,)).fetchall()
        return result(conn, row, adjust_from(rows), MESSAGES[body.action])


@app.post("/api/requests/{request_id}/introduction", response_model=Introduction)
def introduction(request_id: uuid.UUID, body: IntroductionRequest):
    with STATE["pool"].connection() as conn:
        row = stored(conn, request_id)
        leads = {l["unit_id"]: l for g in row["leads"]["groups"] for l in g["leads"]}
        missing = [u for u in body.unit_ids if u not in leads]
        if missing:
            raise HTTPException(422, f"units not among this request's leads: {missing}")
        fb = conn.execute("SELECT unit_id, need_id, action FROM app.feedback WHERE request_id = %s ORDER BY created_at",
                          (request_id,)).fetchall()
        intro = Introduction(id=uuid.uuid4(), request_id=request_id, card=NeedCard(**row["need_card"]),
                             leads=[leads[u] for u in body.unit_ids], feedback=[FeedbackRequest(**f) for f in fb],
                             message=body.message, status="new", created_at=datetime.now(timezone.utc))
        conn.execute("INSERT INTO app.introductions VALUES (%s,%s,%s,%s,%s,%s)",
                     (intro.id, request_id, body.unit_ids, intro.model_dump_json(), intro.status, intro.created_at))
        return intro


@app.get("/api/requests/{request_id}/report.pdf")
def report_pdf(request_id: uuid.UUID):
    from . import report
    with STATE["pool"].connection() as conn:
        stored(conn, request_id)
        return Response(report.render(conn, request_id), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="navigator-report-{request_id}.pdf"'})


@app.get("/api/health", response_model=Health)
def health():
    with STATE["pool"].connection() as conn:
        domains = {d: dict(conn.execute(sql.SQL("SELECT id AS build_id, counts, model_id FROM {}.build").format(
            sql.Identifier(f"live_{d}"))).fetchone()) for d in STATE["domains"]}
    return Health(domains=domains, models={"8b": env("APERTUS_8B"), "70b": env("APERTUS_70B"), "embedding": embed.MODEL_ID,
                                           "reranker": "@".join(embed.RERANKER)})
