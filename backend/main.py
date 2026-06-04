"""
Food 'n' Reps — FastAPI application entry point.

This file wires together the application: middleware, routers, lifespan.
It intentionally contains no business logic — that belongs in the service layer.

Sprint 0: Health check only. Routers are registered as each sprint completes.
Sprint 4: Uncomment router registrations as routes are built.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from core.config import settings
from infrastructure.db.session import AsyncSessionLocal, engine


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application startup and shutdown lifecycle.

    Startup: nothing to initialise yet (connection pool is lazy).
    Shutdown: dispose the engine to cleanly close all pool connections.

    Design choice: We do not eagerly create the connection pool at startup.
    SQLAlchemy's async engine creates connections lazily on first use.
    This keeps startup fast and avoids connection errors if the DB is
    temporarily unreachable at deploy time.
    """
    yield  # application runs here
    await engine.dispose()


# ── Application factory ───────────────────────────────────────────────────────

app = FastAPI(
    title="Food 'n' Reps",
    description=(
        "Multi-role fitness coaching platform. "
        "Clients, fitness trainers, nutritionists, master coaches, and super admins."
    ),
    version="0.1.0",
    lifespan=lifespan,
    # Swagger UI available at /docs, ReDoc at /redoc
)


# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,      # required for httpOnly cookie (refresh token)
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers (registered as sprints complete) ──────────────────────────────────
#
# Sprint 4 — uncomment these as routes are built:
#
# from presentation.api.routes import auth, client, trainer, nutritionist, coach, admin
# app.include_router(auth.router,         prefix="/auth",         tags=["Auth"])
# app.include_router(client.router,       prefix="/client",       tags=["Client"])
# app.include_router(trainer.router,      prefix="/trainer",      tags=["Trainer"])
# app.include_router(nutritionist.router, prefix="/nutritionist", tags=["Nutritionist"])
# app.include_router(coach.router,        prefix="/coach",        tags=["Coach"])
# app.include_router(admin.router,        prefix="/admin",        tags=["Admin"])


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Health check with DB connectivity")
async def health_check() -> dict[str, str]:
    """
    Returns application health status and database connectivity.

    Design choice: The health check actively tests the DB connection
    (SELECT 1) rather than just returning a static 200. This makes it
    usable as a Docker HEALTHCHECK and a Kubernetes readiness probe —
    it distinguishes "app is running" from "app can serve requests".

    Used by: Docker Compose healthcheck, future load balancer probes.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "unreachable"

    return {
        "status": "healthy",
        "db": db_status,
        "environment": settings.environment,
    }
