up:     ; docker compose up -d --build
index:  ; docker compose run --rm api navigator index --domain $(DOMAIN)
eval:   ; docker compose run --rm api navigator eval --domain $(DOMAIN) --split $(or $(SPLIT),dev)
test:   ; DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python -m pytest -q
# Host-side development (decision D-03): make dev ARGS="fetch --domain medtech"
dev:    ; set -a && . ./.env && set +a && DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/navigator $(ARGS)
api:    ; set -a && . ./.env && set +a && DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python -m uvicorn navigator.api:app --port 8000
web:    ; cd web && npm run dev
