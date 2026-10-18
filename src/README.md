# Research & Expertise Navigator

Helps a company looking at Bern find research groups, facilities and support programmes at the University of Bern and the Diabetes Center Berne. Built for the Hack Apertus challenge of the Bern Economic Development Agency. Every lead quotes the public page it comes from; introductions go through the agency.

- `plan.md`: the specification.
- `docs/superpowers/plans/2026-10-18-navigator.md`: the implementation plan.
- `flow.md`: the end-to-end flow and the code that implements each step.
- `decision.md`: decisions taken while building.
- `issues.md`: problems met and how they were solved.

## Run it

```bash
cp .env.example .env          # fill in DB_PASSWORD, APERTUS_API_KEY; every setting is required
docker compose up -d --build  # db (Postgres 16 + pgvector), api (FastAPI), web (React) on http://localhost:8080
make index DOMAIN=medtech     # fetch, extract, enrich (Apertus), embed (BGE-M3), load, check, go live
make eval DOMAIN=medtech      # recall@10 and the other measures on the answer key (SPLIT=all for the hold-out)
```

The API does not start until a live index exists and the Apertus gateway lists the configured models.

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
make api      # http://localhost:8000
make web      # http://localhost:5173, proxies /api to port 8000
```

## Sovereignty

Apertus is the only language model. It is reached through an OpenAI-compatible address (`APERTUS_BASE_URL`), so it moves from the hackathon gateway to a self-hosted vLLM server with no code change. Embeddings (BGE-M3) and the reranker (bge-reranker-v2-m3) are open-weights models running locally. No other outside service is used at run time.

## Adding a site

Add one host line to `config/domains/medtech.yaml` and run `make index DOMAIN=medtech` again. Only the new host is fetched, and only its new pages are sent to Apertus and the embedding model.

## Data

Page text belongs to the institutions. The repository ships code and evaluation files only. `navigator snapshot export <dir>` and `navigator snapshot import <dir>` share the dataset and the model caches within the team. MeSH data: courtesy of the U.S. National Library of Medicine. German MeSH: ZB MED, CC BY 4.0. Wikidata: CC0.
