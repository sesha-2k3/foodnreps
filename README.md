# Food 'n' Reps

Multi-role fitness coaching platform. Clients, fitness trainers, nutritionists,
master coaches, and super admins — each with their own domain over workout
programmes and diet plans.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python 3.14 |
| ORM | SQLAlchemy 2.0 async |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Package manager | uv |
| Frontend | React + Vite + TypeScript (Sprint 5) |

---

## Quick start

**Prerequisites:** Docker, Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/)

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd food_n_reps

# 2. Copy environment variables
cp .env.example .env
# Edit .env — change JWT_SECRET before running in production

# 3. Start PostgreSQL
make up

# 4. Install Python dependencies
make install

# 5. Run database migrations (Sprint 2 — first time will be a no-op)
make upgrade

# 6. Start the development server
make dev
# → API at http://localhost:8000
# → Swagger UI at http://localhost:8000/docs
```

---

## Common commands

```bash
make help           # list all commands with descriptions

make up             # start PostgreSQL in Docker
make down           # stop all Docker services
make dev            # run FastAPI dev server (hot reload)

make migrate MSG="add users table"   # generate a new migration
make upgrade        # apply pending migrations
make downgrade      # roll back one migration
make history        # show migration history

make test           # run full test suite
make test-unit      # unit tests only (no DB)
make test-integration # integration tests (DB required)

make lint           # ruff + mypy
make format         # auto-format with ruff
make check          # full quality gate (run before pushing)
```

---

## Project structure

```
food_n_reps/
├── backend/
│   ├── core/           # config, exceptions, security (no layer deps)
│   ├── domain/         # entities + repository interfaces (pure Python)
│   ├── application/    # services + factories (business logic)
│   ├── infrastructure/ # ORM models, repositories, DB session
│   ├── presentation/   # FastAPI routes, schemas, middleware
│   ├── tests/          # unit/ and integration/ test suites
│   ├── alembic/        # migration scripts
│   └── main.py         # FastAPI app factory
├── frontend/           # React + Vite (Sprint 5)
├── docker-compose.yml
├── .env.example
└── Makefile
```

---

## Architecture

See the companion documents:

- `fitness_tracker_architecture.md` — layered monolith design, service map, patterns
- `food_n_reps_schema.md` — full database schema with design rationale
- `food_n_reps_build_plan.md` — sprint-by-sprint build plan with design decisions

---

## Sprint status

| Sprint | Layer | Status |
|---|---|---|
| S0 — Project bootstrap | Setup | Complete |
| S1 — Domain layer | Domain | Complete |
| S2 — Infrastructure layer | Infrastructure | Complete |
| S3 — Application layer | Application | Complete |
| S4 — Presentation layer | Presentation | Complete |
| S5 — Frontend foundation | Frontend | Complete |
| S6 — FitnessTable component | Frontend | Complete |
| S7 — Client views | Frontend | Complete |
| S8 — Coach + trainer views | Frontend | . |
| S9 — Admin views | Frontend | . |
| S10 — Cross-cutting features | Full stack | . |



trainer: trainer@foodnreps.com / trainer123
client: client@foodnreps.com / client123
admin: admin@foodnreps.com / admin123

```javascript
fetch('/auth/logout', { method: 'POST', credentials: 'include' })
  .then(() => { window.location.href = '/login'; })
```