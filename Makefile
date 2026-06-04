.PHONY: help up down logs install dev migrate upgrade downgrade history \
        test test-unit test-integration lint format check

# ─── Default target ──────────────────────────────────────────────────────────

help: ## Show all available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ─── Docker ──────────────────────────────────────────────────────────────────

up: ## Start PostgreSQL (and all services) in the background
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Follow logs for all services
	docker compose logs -f

# ─── Python environment ───────────────────────────────────────────────────────

install: ## Install all Python dependencies including dev extras
	cd backend && uv sync --all-extras

# ─── Development server ───────────────────────────────────────────────────────

dev: ## Run the FastAPI dev server locally (hot reload)
	cd backend && uv run uvicorn main:app --reload --port 8000

# ─── Database / Alembic ──────────────────────────────────────────────────────

migrate: ## Generate a new migration  (usage: make migrate MSG="add users table")
	cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

upgrade: ## Apply all pending migrations
	cd backend && uv run alembic upgrade head

downgrade: ## Roll back one migration
	cd backend && uv run alembic downgrade -1

history: ## Show migration history
	cd backend && uv run alembic history --verbose

# ─── Tests ───────────────────────────────────────────────────────────────────

test: ## Run the full test suite
	cd backend && uv run pytest -v

test-unit: ## Run unit tests only (no DB required)
	cd backend && uv run pytest tests/unit/ -v

test-integration: ## Run integration tests only (DB required)
	cd backend && uv run pytest tests/integration/ -v

# ─── Code quality ────────────────────────────────────────────────────────────

lint: ## Run ruff linter + mypy type checker
	cd backend && uv run ruff check . && uv run mypy .

format: ## Auto-format code with ruff
	cd backend && uv run ruff format .

check: ## Full quality gate: lint + format check + types (run before committing)
	cd backend && uv run ruff check . \
		&& uv run ruff format --check . \
		&& uv run mypy .
