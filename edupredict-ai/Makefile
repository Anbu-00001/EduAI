# EduPredict AI — Project Makefile

# ── Frontend build ──────────────────────────────────────────
build-ui:
	cd app/ui && npm ci && npm run build

# Frontend dev server (with API proxy to :8000)
dev-ui:
	cd app/ui && npm run dev

# ── Backend dev server ──────────────────────────────────────
dev-api:
	uvicorn app.api.main:app --reload --port 8000

# Run API + UI dev servers in parallel
dev:
	$(MAKE) -j2 dev-api dev-ui

# ── Full production build ───────────────────────────────────
build:
	$(MAKE) build-ui
	docker compose build

# ── Install UI dependencies ─────────────────────────────────
install-ui:
	cd app/ui && npm ci

# ── Clean old frontend artifacts ────────────────────────────
clean-frontend:
	rm -f app/frontend/index.html
	find app/api/static/ -type f -delete
	@echo "Old frontend files removed. Run 'make build-ui' to rebuild."

# ── Testing ─────────────────────────────────────────────────
test:
	python -m pytest tests/ -v

test-ci:
	python -m pytest tests/ -v --tb=short

typecheck-ui:
	cd app/ui && npm run typecheck

# ── Docker ──────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f api

# ── Help ────────────────────────────────────────────────────
help:
	@echo "EduPredict AI — Available targets:"
	@echo "  make dev          — Run API + UI dev servers in parallel"
	@echo "  make dev-api      — FastAPI backend only (port 8000)"
	@echo "  make dev-ui       — Vite frontend only (port 5173)"
	@echo "  make build-ui     — Build React frontend -> app/api/static/"
	@echo "  make build        — Full prod build (UI + Docker)"
	@echo "  make test         — Run pytest suite"
	@echo "  make typecheck-ui — TypeScript typecheck"
	@echo "  make up           — docker compose up -d"
	@echo "  make clean-frontend — Remove old static files"

.PHONY: build-ui dev-ui dev-api dev build install-ui clean-frontend test test-ci typecheck-ui up down logs help
