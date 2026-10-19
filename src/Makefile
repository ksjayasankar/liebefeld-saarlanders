.PHONY: up index eval test dev api web dump restore
up:     ; docker compose up -d --build
index:  ; docker compose run --rm api navigator index --domain $(DOMAIN)
eval:   ; docker compose run --rm api navigator eval --domain $(DOMAIN) --split $(or $(SPLIT),dev)
test:   ; DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python -m pytest -q
# Host-side development (decision D-03): make dev ARGS="fetch --domain medtech"
dev:    ; set -a && . ./.env && set +a && DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/navigator $(ARGS)
api:    ; set -a && . ./.env && set +a && DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python -m uvicorn navigator.api:app --port 8000
web:    ; cd web && npm run dev
# The built index (live_medtech), the model caches and the migrations as one Postgres dump, so a fresh checkout skips
# the hours-long `make index`: `make restore` loads it into the database, then `make up` starts the system.
INDEX_URL = https://github.com/ksjayasankar/liebefeld-saarlanders/releases/download/index-v1/index.dump
dump:
	docker compose exec -T db pg_dump -U navigator -d navigator -Fc -n app -n cache -n dataset -n 'live_*' \
	  --exclude-table-data=app.requests --exclude-table-data=app.feedback --exclude-table-data=app.introductions > index.dump
restore:
	test -f index.dump || curl -fL -o index.dump $(INDEX_URL)
	docker compose up -d --wait db
	docker compose exec -T db psql -U navigator -d navigator -c "CREATE EXTENSION IF NOT EXISTS vector"
	docker compose exec -T db pg_restore -U navigator -d navigator --clean --if-exists --no-owner < index.dump
