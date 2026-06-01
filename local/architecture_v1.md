# Fitness Tracker — Architecture & Design Document

> **Status:** Planning complete, development not yet started.  
> **Stack:** Python · FastAPI · PostgreSQL · React · Docker  
> **Pattern:** Layered Monolith (Clean Architecture)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Decision: Why Layered Monolith](#2-architecture-decision-why-layered-monolith)
3. [Architecture Progression Path](#3-architecture-progression-path)
4. [Tech Stack Decisions](#4-tech-stack-decisions)
5. [System Layers](#5-system-layers)
6. [Application Services](#6-application-services)
7. [Design Patterns Applied](#7-design-patterns-applied)
8. [Authentication Design](#8-authentication-design)
9. [Database Strategy](#9-database-strategy)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Project Structure](#11-project-structure)
12. [Build Order](#12-build-order)
13. [Suggested Improvements & Edge Cases](#13-suggested-improvements--edge-cases)

---

## 1. Project Overview

A fitness tracker application with two roles: **Admin** and **Client**.

**Client experience:** After login, a client sees a welcome screen and can navigate to their Workout Plan or Diet Plan. Both plans are displayed in a spreadsheet-style table. Plans are read-only for the client — they cannot modify them.

**Admin experience:** The admin can view all clients, edit any client's workout or diet plan, and manage client accounts. The admin can also maintain their own personal plans.

**Workout plan fields:** exercise name, sets, reps.

**Diet plan fields:** food name, calories, protein, fat, carbs.

---

## 2. Architecture Decision: Why Layered Monolith

### What problem does architecture solve?

Without structure, a change in one part of a codebase cascades unpredictably into others. Architecture is a strategy for **containing change propagation**. The goal is not elegance for its own sake — it is making future changes, debugging, and testing as cheap as possible.

### Why layered (not microservices, not event-driven)?

We evaluated four options:

| Architecture | Verdict | Reason |
|---|---|---|
| Layered Monolith | **Selected** | Right size for the team and problem. Teaches correct patterns. Easy to evolve. |
| Modular Monolith | Future step | Natural next stage when the team grows or features multiply. |
| Microservices | Rejected | Massive operational overhead for no current benefit. Distributed systems failures for a single-team app. |
| Event-Driven | Rejected | Unnecessary complexity. No fan-out workflows exist yet. |

The industry consensus, confirmed by experience: start with a well-structured monolith. Migrate to microservices only when you have a **concrete, measurable problem** — a team that cannot coordinate, or a specific service with 10x the load of others. Anticipated problems are not a reason to add complexity today.

### The core rule: dependency direction

Each layer only knows about the layer directly below it. The inner layers (Domain) have zero knowledge of the outer layers (Infrastructure, Presentation). This is enforced strictly, not by convention.

```
Presentation  →  Application  →  Domain  ←  Infrastructure
```

Infrastructure's arrow points toward Domain (not away from it). This is **dependency inversion**: Infrastructure implements contracts that Domain defines. Domain never imports from Infrastructure — ever.

### Tradeoffs accepted

**We gain:** clear boundaries, testability, cognitive locality (you know exactly which layer to look in when something breaks), and a natural migration path to modular or microservices architecture.

**We give up:** the simplicity of a flat script. There is more boilerplate than a quick-and-dirty approach. For a project intended to last and grow, this is the right trade.

---

## 3. Architecture Progression Path

The planned evolution if the application grows beyond its current scope:

```
Stage 1: Layered Monolith       ← we are here
  Organized by:   Technical layer (services/, repositories/, routes/)
  Boundaries:     Folders (soft — enforced by discipline)
  Database:       One schema, shared freely
  Trigger to move: Team friction, cognitive overload per feature

        ↓  Reorganize folders by business domain

Stage 2: Modular Monolith
  Organized by:   Business domain (workout/, diet/, auth/, user/)
  Boundaries:     Public module __init__.py (enforced by import-linter in CI)
  Database:       One DB, beginning to think about ownership per domain
  Trigger to move: DB coupling pain, need team ownership per domain

        ↓  Separate data ownership, introduce internal event bus

Stage 3: Domain-Oriented Architecture
  Organized by:   Business domain (same as Stage 2)
  Boundaries:     Data ownership + event contracts (airtight)
  Database:       One DB, separate PostgreSQL schemas per domain
  Communication:  In-process event bus (no Kafka yet)
  Trigger to move: One domain genuinely needs independent scaling/deployment

        ↓  Extract one service at a time (Strangler Fig pattern)

Stage 4: Selective Microservices
  Organized by:   Business domain (now separate repos)
  Boundaries:     Network + independent databases (hard boundaries)
  Database:       Separate DB per extracted service
  Communication:  Message broker (Kafka/RabbitMQ) + HTTP/gRPC
  Trigger to move: Never, unless a concrete problem demands it
```

### Migration rules

Each stage is a **prerequisite** for the next. You cannot safely extract a microservice from a layered monolith — there are too many hidden dependencies. But you can extract cleanly from a domain-oriented monolith because the isolation work was done in earlier stages.

**Stage 1 → 2:** Move files from `application/services/workout_service.py` to `modules/workout/service.py`. Each module exposes a single `__init__.py` as its public interface. Nothing else is importable from outside the module. Use `import-linter` in CI to enforce this.

**Stage 2 → 3:** Separate database table ownership per domain (no cross-domain foreign keys). Replace direct cross-domain service calls with an internal event bus. Use PostgreSQL schemas to namespace tables.

**Stage 3 → 4:** Extract using the **Strangler Fig pattern** — deploy the new service alongside the monolith, route a percentage of traffic to it, validate, increase gradually, then remove from the monolith. Never do a big-bang extraction.

---

## 4. Tech Stack Decisions

### Backend

| Tool | Version | Decision & Rationale | Tradeoff |
|---|---|---|---|
| Python | 3.12+ | Team language, strong async support, rich ML/health ecosystem for future | Slower raw performance than Go/Rust, but irrelevant at this scale |
| FastAPI | Latest | Type-safe, async-native, auto-generates OpenAPI docs, built-in DI via `Depends()` | More opinionated than Flask; learning curve for DI pattern |
| SQLAlchemy | 2.0 async | Mature ORM, excellent async support, pairs naturally with Repository pattern | More verbose than Django ORM; intentional — we want that separation |
| PostgreSQL | 16 | Relational model is the right fit for structured plan data; strong JSON support for future | Requires Docker for local dev; worth it for parity with production |
| Alembic | Latest | Version-controlled migrations, supports upgrade/downgrade, production-safe | More setup than `create_all()`; necessary for any real project |
| Pydantic | v2 | Integrated with FastAPI, fast (Rust core), doubles as request/response schema layer | v2 is not backward compatible with v1; use v2 from the start |
| python-jose | Latest | JWT encoding/decoding, supports RS256 and HS256 | Relatively low-level; intentional — gives full control over token lifecycle |
| bcrypt | Latest | Industry-standard password hashing; intentionally slow to resist brute force | Adds ~100ms to login; acceptable and correct |
| pytest + pytest-asyncio | Latest | Native async test support, fixtures align well with FastAPI's DI | — |

### Frontend

| Tool | Decision & Rationale | Tradeoff |
|---|---|---|
| React + Vite | Fast dev server, component model, massive ecosystem | More setup than Create React App; Vite is worth it |
| TanStack Table | Headless, composable, spreadsheet-like behavior without opinionated UI | More setup than a turnkey table library; intentional — we want full control |
| TanStack Query | Cache-aware data fetching, pairs with TanStack Table, handles refresh token silently | Adds abstraction; worth it for automatic retry and cache invalidation |
| React Router | Standard SPA routing; supports role-based route guards | — |
| Tailwind CSS | Utility-first, no CSS naming conventions to debate, fast iteration | Large class lists in JSX; manageable with component extraction |
| Axios | Interceptors make silent JWT refresh straightforward to implement | Slightly heavier than `fetch`; interceptor pattern justifies it |

### Infrastructure

| Tool | Decision & Rationale |
|---|---|
| Docker + Docker Compose | Single command to run the full stack. Eliminates "works on my machine." Production parity from day one. |
| PostgreSQL (Dockerized) | Named volumes persist data across container restarts. No SQLite inconsistencies. |

---

## 5. System Layers

### Layer 1: Presentation

**Responsibility:** Accept HTTP requests, validate input shape, delegate to services, return HTTP responses.

**What lives here:** FastAPI route files (auth, client, admin), Pydantic request/response schemas, middleware (JWT validation, role guards, CORS), and FastAPI `Depends()` wiring.

**What does NOT live here:** Business logic. If a route handler contains an `if` statement that isn't about HTTP concerns, that logic belongs in the Application layer.

**Pattern:** Strategy (role-based access). Admin and Client share route structures but have different permission strategies enforced at the middleware level, not with `if/else` chains inside handlers.

### Layer 2: Application

**Responsibility:** Orchestrate use cases. Coordinate between domain entities and repository interfaces. Enforce application-level rules.

**What lives here:** The five services (`AuthService`, `ClientService`, `AdminService`, `WorkoutService`, `DietService`), the two factories (`WorkoutFactory`, `DietFactory`), and use-case logic (e.g., "deactivate old plan before activating new one").

**What does NOT live here:** SQL queries, ORM models, HTTP concerns, or direct database access.

**Pattern:** Service Layer, Factory.

### Layer 3: Domain

**Responsibility:** Define what the business domain *is* — its entities, its rules, and its contracts.

**What lives here:** Pure Python dataclasses representing domain entities (`User`, `WorkoutPlan`, `WorkoutEntry`, `DietPlan`, `DietEntry`), and abstract base classes defining the repository and service interfaces (contracts).

**What does NOT live here:** Anything that imports from outside the standard library. Zero external dependencies. This layer must be testable with `pytest` alone, with no database, no framework, no network.

**This is the most important constraint in the entire architecture.** The domain is the heart of the system. If it has no external dependencies, it can never break because of a framework upgrade, a database change, or an infrastructure decision.

**Pattern:** Repository (interface definition only).

### Layer 4: Infrastructure

**Responsibility:** Implement the contracts defined in Domain using real technology (PostgreSQL, SQLAlchemy).

**What lives here:** Concrete repository implementations (`UserRepository`, `WorkoutRepository`, `DietRepository`), SQLAlchemy ORM models, the async database session singleton, and Alembic migration files.

**Critical distinction — ORM models are NOT domain entities.** SQLAlchemy models in `infrastructure/db/models.py` represent how data is stored. Domain entities in `domain/entities/` represent what data means. Repositories are the bridge — they map between the two. This separation means business logic is free of ORM decorators and database coupling, and can be unit-tested without a database.

**Pattern:** Repository (concrete implementation), Singleton (DB session).

---

## 6. Application Services

### Service boundaries and ownership

```
AuthService      →  owns: login, logout, JWT lifecycle, password hashing
                    injects: IUserRepository, core.security, core.config
                    refuses: user creation, profile management, plan logic

ClientService    →  owns: read own profile, read own workout plan, read own diet plan
                    injects: IUserRepository, IWorkoutRepository, IDietRepository
                    refuses: any mutation — no create/update/delete methods exist on this class

AdminService     →  owns: CRUD on client accounts, plan assignment, own personal plans
                    injects: IUserRepository, WorkoutService, DietService
                    refuses: direct IWorkoutRepository / IDietRepository access for mutations
                    note: the ONLY service that calls other services

WorkoutService   →  owns: create/edit/delete workout plans and entries, one-active-plan rule
                    injects: IWorkoutRepository, WorkoutFactory
                    refuses: diet logic, user account management, auth

DietService      →  owns: create/edit/delete diet plans and entries, one-active-plan rule
                    injects: IDietRepository, DietFactory
                    refuses: workout logic, user account management, auth
```

### The delegation rule

`AdminService` is the only service that calls other services. When an admin assigns or edits a client's workout plan, `AdminService` calls `WorkoutService.create_plan(...)` — it does not write to `IWorkoutRepository` directly. This ensures business rules for plans are enforced in exactly one place.

### Three rules all services must follow

1. **Never instantiate dependencies.** Everything injected through the constructor. This enables unit testing with mock repositories — no database required.

2. **Never touch ORM models.** Services receive and return domain entities only. The mapping between ORM models and domain entities is the repository's sole job.

3. **Raise domain exceptions, not HTTP exceptions.** A service raises `ClientNotFoundError`, not `HTTPException(404)`. The route layer catches domain exceptions and translates them. This keeps business logic free of web framework concerns.

---

## 7. Design Patterns Applied

| Pattern | Where | Why |
|---|---|---|
| Repository | Domain (interface) + Infrastructure (implementation) | Abstracts all database access behind a contract. Swap PostgreSQL for any other store by rewriting only the repository — zero changes to business logic. |
| Service Layer | Application | One class owns one set of use cases. No logic scattered across routes or models. |
| Factory | Application (`WorkoutFactory`, `DietFactory`) | Centralizes object construction. A `WorkoutPlan` is never built with a plain constructor call in business code — the factory enforces that it is valid before it exists. |
| Strategy | Presentation (role-based access) | Admin and Client have different permission sets. Encoded as strategies, not `if role == "admin"` chains spread across handlers. |
| Singleton | Infrastructure (DB session) | One connection pool, shared safely across the application lifetime. |
| Dependency Injection | All layers via FastAPI `Depends()` | Services and repositories are injected into routes, never instantiated inside them. Makes every unit independently testable. |
| Facade | Frontend (`FitnessTable` component) | Wraps TanStack Table behind a custom API. The rest of the app never imports TanStack directly. Replacing TanStack is a one-file change. |

---

## 8. Authentication Design

### Token architecture

| Token | Lifetime | Storage | Contains |
|---|---|---|---|
| Access token (JWT) | 15 minutes | Memory only (JS variable) | `user_id`, `role`, `exp` |
| Refresh token (JWT) | 7 days | `httpOnly` cookie | `user_id`, `token_id`, `exp` |

**Why memory for the access token:** `localStorage` is readable by any JavaScript on the page, making it vulnerable to XSS. Storing the access token in a JS variable means it lives only for the page session and is inaccessible to injected scripts.

**Why httpOnly cookie for the refresh token:** httpOnly cookies are completely inaccessible to JavaScript. CSRF is mitigated by requiring the `Authorization: Bearer <access_token>` header on all state-changing requests — a CSRF attack cannot set that header.

### Silent refresh flow

TanStack Query's retry interceptor handles token expiry transparently:

1. Request fires with access token in `Authorization` header.
2. Server returns `401 Unauthorized`.
3. Axios interceptor catches the 401, fires `POST /auth/refresh` (the httpOnly cookie is sent automatically).
4. Server validates the refresh token, returns a new access token.
5. Interceptor retries the original request with the new token.
6. The user sees nothing — no logout, no redirect.

### Role encoding

Roles (`admin`, `client`) are encoded in the access token payload. Middleware decodes the token and attaches the role to the request context. Route handlers and services receive the role from context — they never re-query the database for it.

---

## 9. Database Strategy

### Schema design principles

- Every table has a `UUID` primary key (not auto-increment integer). UUIDs are safe to expose in URLs and are merge-safe if the database ever shards.
- Every table has `created_at` and `updated_at` timestamps, set automatically.
- Plans have an `is_active` boolean. Only one workout plan and one diet plan may be active per client at a time. This constraint is enforced at the service layer, with a partial unique index as a safety net.

### Alembic workflow

```
# Generate a migration after changing ORM models
alembic revision --autogenerate -m "add_diet_plan_table"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration (for development mistakes)
alembic downgrade -1
```

Migrations are version-controlled alongside code. Every pull request that changes an ORM model must include the corresponding migration file.

### Docker Compose database setup

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: fitness
      POSTGRES_PASSWORD: fitness
      POSTGRES_DB: fitness_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

The named volume `postgres_data` persists data across `docker compose down` and `docker compose up` cycles. Data is only lost with `docker compose down -v`.

---

## 10. Frontend Architecture

### Routing and role guards

```
/login                      → public
/client/dashboard           → requires role: client
/client/workout             → requires role: client
/client/diet                → requires role: client
/admin/dashboard            → requires role: admin
/admin/clients              → requires role: admin
/admin/clients/:id/workout  → requires role: admin
/admin/clients/:id/diet     → requires role: admin
```

Route guards read the role from the decoded access token. If the token is absent or expired on page load, the guard fires a silent refresh before deciding whether to redirect to login.

### The FitnessTable component (Facade pattern)

The entire application uses `FitnessTable` and knows nothing about TanStack Table. TanStack is an implementation detail hidden inside `_tanstack.tsx` (the underscore prefix signals: internal, do not import).

**Public API exposed to the rest of the app:**

```tsx
interface FitnessTableProps<T> {
  columns: ColumnDef<T>[]   // your column definitions — typed to your domain
  data: T[]                  // your row data
  onRowEdit?: (row: T) => void
  onRowDelete?: (id: string) => void
  onAddRow?: () => void
  editable?: boolean         // single flag, not TanStack configuration
  loading?: boolean
}

<FitnessTable
  columns={workoutColumns}
  data={entries}
  onRowEdit={handleEdit}
  editable={isAdmin}
/>
```

If TanStack is ever replaced — with AG Grid, a hand-rolled table, or anything else — `_tanstack.tsx` is rewritten and nothing else changes. Every page that renders a table continues working with zero import changes.

---

## 11. Project Structure

```
fitness_tracker/
│
├── backend/
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── user.py              # User dataclass, Role enum (admin | client)
│   │   │   ├── workout.py           # WorkoutPlan, WorkoutEntry dataclasses
│   │   │   └── diet.py              # DietPlan, DietEntry dataclasses
│   │   └── interfaces/
│   │       ├── repositories.py      # IUserRepo, IWorkoutRepo, IDietRepo (ABC)
│   │       └── services.py          # IAuthService, IWorkoutService, etc. (ABC)
│   │
│   ├── application/
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── client_service.py
│   │   │   ├── admin_service.py
│   │   │   ├── workout_service.py
│   │   │   └── diet_service.py
│   │   └── factories/
│   │       ├── workout_factory.py
│   │       └── diet_factory.py
│   │
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── models.py            # SQLAlchemy ORM models (NOT domain entities)
│   │   │   ├── session.py           # Async session singleton
│   │   │   └── migrations/          # Alembic env.py + versions/
│   │   └── repositories/
│   │       ├── user_repository.py
│   │       ├── workout_repository.py
│   │       └── diet_repository.py
│   │
│   ├── presentation/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── client.py
│   │   │   │   └── admin.py
│   │   │   ├── schemas/
│   │   │   │   ├── workout_schema.py
│   │   │   │   └── diet_schema.py
│   │   │   └── dependencies.py      # FastAPI Depends() wiring
│   │   └── middleware/
│   │       ├── auth_guard.py        # JWT decode + role verification
│   │       └── cors.py
│   │
│   ├── core/
│   │   ├── config.py                # pydantic-settings, reads .env, validated on startup
│   │   ├── security.py              # JWT encode/decode utilities
│   │   └── exceptions.py            # Custom exception hierarchy
│   │
│   ├── tests/
│   │   ├── unit/                    # Services + factories, no DB, mock repos
│   │   └── integration/             # Routes with real test DB
│   │
│   ├── main.py                      # FastAPI app factory + router registration
│   ├── alembic.ini
│   └── pyproject.toml
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── table/
│       │   │   ├── FitnessTable.tsx     # Public Facade component
│       │   │   ├── types.ts             # FitnessTableProps (your API contract)
│       │   │   └── _tanstack.tsx        # TanStack internals (never imported elsewhere)
│       │   └── ui/                      # Shared: Button, Badge, Spinner, etc.
│       ├── pages/
│       │   ├── Login.tsx
│       │   ├── client/
│       │   │   ├── Dashboard.tsx
│       │   │   ├── WorkoutView.tsx
│       │   │   └── DietView.tsx
│       │   └── admin/
│       │       ├── Dashboard.tsx
│       │       └── ClientEditor.tsx
│       ├── services/
│       │   ├── api.ts                   # Axios instance + refresh interceptor
│       │   └── auth.ts                  # Token memory store, decode utilities
│       └── main.tsx
│
└── docker-compose.yml
```

---

## 12. Build Order

This order is non-negotiable. Each step is a prerequisite for the next.

1. **Domain entities + interfaces** — pure Python dataclasses, zero external deps, fully testable immediately. This is the contract everything else is built around.

2. **Docker Compose + PostgreSQL + ORM models + initial Alembic migration** — define how data is stored. Run `alembic upgrade head` and confirm tables exist.

3. **Repository implementations** — connect domain entities to the ORM. Write integration tests against a real test database.

4. **Services + factories** — business logic, tested with mock repositories (no database required for unit tests).

5. **FastAPI routes + schemas + middleware** — thin handlers that delegate immediately to services. Integration tests via FastAPI's `TestClient`.

6. **Frontend** — auth flow first, then client views, then admin views, then `FitnessTable`.

---

## 13. Suggested Improvements & Edge Cases

These are improvements not yet in the plan that should be addressed before or during development to prevent failures, data loss, and security issues.

---

### Security

#### S1 — Rate limiting on auth endpoints

**Risk:** Without rate limiting, the `/auth/login` and `/auth/refresh` endpoints are open to brute-force attacks. An attacker can try thousands of passwords per minute.

**Fix:** Add `slowapi` (FastAPI-compatible rate limiter) to the middleware stack. Apply a strict limit to auth endpoints: 5 requests per minute per IP on `/auth/login`, 10 per minute on `/auth/refresh`. These limits are configurable via environment variables so they can be relaxed in development.

#### S2 — Refresh token rotation and revocation

**Risk:** The current design issues a refresh token that is valid for 7 days with no revocation mechanism. If a refresh token is stolen, the attacker has 7 days of access.

**Fix:** Implement refresh token rotation. Each time a refresh token is used, invalidate it and issue a new one. Store a `token_id` (UUID) in the database alongside its `is_revoked` flag. On every refresh request, verify the `token_id` is not revoked before issuing a new access token. On logout, mark the token as revoked. This adds one DB lookup per refresh but closes the stolen-token window.

#### S3 — CORS locked to specific origins

**Risk:** A wildcard CORS config (`allow_origins=["*"]`) allows any website to make credentialed requests to the API.

**Fix:** `allow_origins` should be set from an environment variable and default to `["http://localhost:5173"]` in development, `["https://your-production-domain.com"]` in production. Never use `"*"` when `allow_credentials=True` — the browser blocks it anyway and it signals a misconfiguration.

#### S4 — JWT secret rotation strategy

**Risk:** If the JWT secret is ever leaked or needs to be rotated, all existing tokens immediately become invalid and all users are logged out simultaneously.

**Fix:** Support multiple active secrets via a `kid` (key ID) header in the JWT. The current secret always signs new tokens; all listed secrets can verify. Rotation is: add new secret to the list, wait for old tokens to expire (15 minutes for access tokens), then remove the old secret. No mass logout. Store secrets as an ordered list in environment config.

---

### Data Integrity

#### D1 — Soft delete, not hard delete

**Risk:** Hard-deleting a client destroys their plan history permanently. If an admin accidentally deletes the wrong client, recovery requires a database backup.

**Fix:** Add `is_deleted: bool` and `deleted_at: datetime | None` to the `User` model. All repository queries filter `WHERE is_deleted = false` by default. A hard delete is never executed by the application — only a DBA can do it. Consider the same for plans.

#### D2 — Plan versioning / audit trail

**Risk:** When an admin edits a client's workout plan, the previous version is overwritten and lost. The client has no history of what changed and when.

**Fix:** Add a `PlanVersion` table that records a snapshot of the plan every time it is modified, along with `modified_by` (the admin's user_id) and `modified_at`. This is essential for a fitness context where the client may want to see progression over time, and for the admin to audit their changes.

#### D3 — Optimistic locking on plan edits

**Risk:** Two admins editing the same client's plan simultaneously can cause a lost update — the second save silently overwrites the first.

**Fix:** Add a `version: int` field to `WorkoutPlan` and `DietPlan`. Every update increments the version. On save, the repository checks `WHERE id = ? AND version = ?`. If the row's version has changed since the edit started, raise a `ConflictError`. The frontend displays "this plan was modified by someone else — please refresh."

#### D4 — Database indexes

**Risk:** As the client list grows, queries like "get all workout entries for user X's active plan" will do full table scans.

**Fix:** Add indexes from the beginning — do not wait for slowness to appear:

```sql
CREATE INDEX idx_workout_entries_plan_id ON workout_entries(plan_id);
CREATE INDEX idx_diet_entries_plan_id ON diet_entries(plan_id);
CREATE UNIQUE INDEX idx_one_active_workout_per_user
  ON workout_plans(user_id) WHERE is_active = true;
CREATE UNIQUE INDEX idx_one_active_diet_per_user
  ON diet_plans(user_id) WHERE is_active = true;
```

The partial unique indexes on `is_active` enforce the one-active-plan-per-client rule at the database level — a second layer of protection if the service-layer check is ever bypassed.

---

### Performance

#### P1 — N+1 query problem in admin client listing

**Risk:** Fetching a list of 100 clients and then fetching each client's active plan in a loop causes 101 queries instead of 1-2. This will be slow and invisible in development (few clients) but painful in production.

**Fix:** The `AdminRepository.list_clients_with_plans()` method must use SQLAlchemy's `selectinload` to eager-load active plans in a single additional query:

```python
stmt = (
    select(UserModel)
    .options(
        selectinload(UserModel.workout_plans.and_(WorkoutPlanModel.is_active == True)),
        selectinload(UserModel.diet_plans.and_(DietPlanModel.is_active == True)),
    )
    .where(UserModel.role == "client")
)
```

Write this correctly from the start — retrofitting eager loading into existing query code is tedious.

#### P2 — Pagination on all list endpoints

**Risk:** `GET /admin/clients` returns every client in the database as a single response. At 1,000 clients this is slow; at 10,000 it times out.

**Fix:** All list endpoints must support `limit` and `offset` (or cursor-based pagination) from day one. The response envelope must include total count:

```json
{
  "data": [...],
  "total": 342,
  "limit": 20,
  "offset": 0
}
```

Adding pagination after the frontend is built is painful — do it on the first endpoint.

#### P3 — Database connection pool configuration

**Risk:** Under concurrent load, too many coroutines waiting for a connection will exhaust the pool and cause timeouts.

**Fix:** Configure the pool explicitly in `session.py`:

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)
```

These values are starting points. Monitor `pool_timeout` errors in logs and tune accordingly.

---

### Developer Experience

#### DX1 — Startup validation of all environment variables

**Risk:** The application starts without error but fails at runtime when it first tries to use a missing env var (e.g., the JWT secret). This is hard to debug in production.

**Fix:** Use `pydantic-settings` for `core/config.py`. Every required environment variable is declared as a typed field with no default. Pydantic validates all of them at import time — the application **refuses to start** if any are missing or malformed. Fast failure is always better than silent failure.

```python
class Settings(BaseSettings):
    database_url: PostgresDsn
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    allowed_origins: list[str]

    model_config = SettingsConfigDict(env_file=".env")
```

#### DX2 — Health check endpoint

**Risk:** Without a health check, Docker and any future deployment platform (Kubernetes, Railway, Fly.io) cannot tell whether the application is ready to serve traffic.

**Fix:** Add `GET /health` to `main.py`. It should: verify the database connection is reachable, return `200 OK` with `{"status": "healthy", "db": "connected"}` on success, or `503 Service Unavailable` if the DB is unreachable. Add this to the Docker Compose `healthcheck` config.

#### DX3 — Seed script for development

**Risk:** Every developer starts with an empty database and must manually create users and plans before they can work on any feature. This creates inconsistency and wastes time.

**Fix:** Create `backend/scripts/seed.py` that creates:
- 1 admin account (`admin@fitness.com` / `admin123`)
- 3 client accounts with pre-populated workout and diet plans

The seed script runs inside the Docker Compose environment: `docker compose exec backend python scripts/seed.py`. It is idempotent — safe to run multiple times without creating duplicates.

#### DX4 — Custom exception hierarchy

**Risk:** Services raising ad-hoc exceptions (generic `ValueError`, `Exception`) means route handlers cannot reliably catch and translate them to the correct HTTP status codes.

**Fix:** Define a structured exception hierarchy in `core/exceptions.py` from the start:

```python
class FitnessTrackerError(Exception):     # base for all app exceptions
    pass

class NotFoundError(FitnessTrackerError):
    pass

class UnauthorizedError(FitnessTrackerError):
    pass

class ForbiddenError(FitnessTrackerError):
    pass

class ConflictError(FitnessTrackerError):  # duplicate, optimistic lock failure
    pass

class ValidationError(FitnessTrackerError):
    pass
```

Register a single FastAPI exception handler that maps these to HTTP status codes. Services raise domain exceptions; routes never need `try/except`.

---

### Frontend Edge Cases

#### FE1 — Token loss on page refresh

**Risk:** The access token lives in memory. On page refresh it is gone. The user sees a loading spinner that never resolves, or is redirected to login even though their session should still be valid.

**Fix:** On application load, before rendering any protected route, fire `POST /auth/refresh` silently. If it succeeds (the httpOnly refresh cookie is still valid), store the new access token in memory and render the app. If it fails (cookie expired or missing), redirect to login. This must complete before the app tree renders — use a loading gate in the root component.

#### FE2 — Concurrent refresh token requests

**Risk:** If five requests fire simultaneously when the access token has expired, all five will hit the 401 handler and all five will try to call `/auth/refresh` at the same time. Depending on the refresh token rotation strategy (see S2), this could invalidate each other's tokens.

**Fix:** The Axios interceptor must use a shared promise for the refresh call. If a refresh is already in progress, all subsequent 401s wait for the same promise to resolve rather than firing their own refresh request:

```typescript
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = api.post('/auth/refresh')
      .then(res => res.data.access_token)
      .finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}
```

#### FE3 — Optimistic UI updates in the admin editor

**Risk:** When an admin saves a plan entry, the UI waits for the server round-trip before updating. On a slow connection this feels sluggish and the user may click save multiple times.

**Fix:** Use TanStack Query's `onMutate` callback for optimistic updates. Update the local cache immediately on save, then reconcile with the server response. On error, roll back the optimistic update and show an error message. This makes the admin editor feel instant.

---

### Operational

#### O1 — Structured logging from day one

**Risk:** When something goes wrong in production, `print()` statements and unstructured logs make it impossible to search, filter, or alert on errors.

**Fix:** Use Python's `logging` module with a JSON formatter (`python-json-logger`) from the first line of production code. Every log entry should include: `timestamp`, `level`, `service`, `user_id` (when available), `request_id` (a UUID generated per request in middleware), and `message`. This makes logs searchable and alertable without any code changes later.

#### O2 — Request ID propagation

**Risk:** When a bug is reported ("my workout plan didn't save"), there is no way to find the specific failing request in the logs.

**Fix:** Middleware generates a UUID `request_id` for every incoming request and attaches it to the request context. It is included in every log line during that request's lifecycle. It is also returned in the response as an `X-Request-ID` header. The frontend logs this header on errors so the user can report it to support.

---

*Document generated during architectural planning sessions. Update this document before beginning any new feature that changes the architecture, adds a service, or modifies the authentication flow.*
