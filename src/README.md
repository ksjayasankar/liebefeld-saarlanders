# Research & Expertise Navigator

A workspace for the Bern Economic Development Agency. A company considering Bern sends its business model; agency staff paste it or upload it as a PDF (read locally with Docling, OCR for scanned pages), confirm the need card Apertus drafts, and get potential collaborators at the University of Bern and the Diabetes Center Berne: research groups, people and contact persons with their functions, expertise, projects and infrastructure. Every claim quotes and links the public page it comes from. Built for the Hack Apertus challenge.

The tool shows contact data collected from public pages and has no login yet: run it only where agency staff alone can reach it.

- `../technical_report.md`: architecture, evaluation and limitations.
- `design_decisions.md`: front-end design decisions.

## Run it

```bash
cp .env.example .env          # fill in DB_PASSWORD (also in DATABASE_URL) and LLM_API_KEY; every setting is required
make restore                  # download the team's built index (275 MB, release index-v1) and load it into Postgres
make up                       # db (Postgres 16 + pgvector), api (FastAPI), web (React) on http://localhost:8080
make eval DOMAIN=medtech      # recall@10 and the other measures on the answer key (SPLIT=all for the hold-out)
```

The first start downloads the local models (BGE-M3, the reranker, Docling) into a Docker volume, which takes a few minutes. The API does not start until a live index exists and the Apertus endpoint lists the configured models (`LLM_NAME`, `LLM_NAME_LARGE`). To build the index from the live sites instead of restoring it, run `make up` and then `make index DOMAIN=medtech` (fetch, extract, enrich with Apertus, embed with BGE-M3, load, check, go live; several hours).

**Development on the host** (macOS, Python 3.11 in `.venv`, database in Docker on port 5433):

```bash
docker compose up -d db
make dev ARGS="migrate"
make dev ARGS="fetch --domain medtech"     # resumable; one request per second per host
make dev ARGS="index --domain medtech"     # or the single steps: extract, enrich, embed, report, load, check
make test
```

**Demo on a Mac.** Docker on macOS cannot use the Apple GPU, so searches in the api container take about 30 s per need. For a demo, run the API on the host with `TORCH_DEVICE=mps` (about 3 s per need) and the front end from Vite:

```bash
docker compose stop api web   # frees port 8000; the db keeps running
make api      # http://localhost:8000
make web      # http://localhost:5173, proxies /api to port 8000
```

## Sovereignty

Apertus is the only language model. It is reached through an OpenAI-compatible address (`LLM_BASE_URL`), so it moves from the hackathon gateway to a self-hosted vLLM server with no code change. Embeddings (BGE-M3) and the reranker (bge-reranker-v2-m3) are open-weights models running locally. No other outside service is used at run time.

## Adding a site

Add one host line to `config/domains/medtech.yaml` and run `make index DOMAIN=medtech` again. A site whose pages need JavaScript gets `render: browser`; it is fetched with headless Chromium (`pip install -e .[render]`, `playwright install --only-shell chromium`). Only the new host is fetched, and only its new pages are sent to Apertus and the embedding model.

## AI Usage

We used Claude Code and ChatGPT to assist with the development of the product prototype and creating report drafts.

## Data

Page text belongs to the institutions. The repository ships code and evaluation files only; the built index (`make dump`, `make restore`) is published separately as a release asset so the system runs without a crawl. `navigator snapshot export <dir>` and `navigator snapshot import <dir>` share the dataset and the model caches within the team. MeSH data: courtesy of the U.S. National Library of Medicine. German MeSH: ZB MED, CC BY 4.0. Wikidata: CC0.
