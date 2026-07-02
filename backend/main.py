"""
Food 'n' Reps — FastAPI application entry point.

Sprint 0: Health check, CORS, lifespan.
Sprint 4: Exception handlers registered, all routers mounted.

Design choice — single FoodNRepsError exception handler:
    One handler catches every domain exception. A dict maps exception type
    → HTTP status. Routes write no try/except — they call services and the
    domain exceptions propagate up to this handler automatically. Adding a
    new exception subclass requires one line in STATUS_MAP.

Design choice — DomainValidationError alias:
    core.exceptions.ValidationError is aliased here because pydantic.ValidationError
    is also imported by FastAPI, which registers its own handler for it (HTTP 422).
    Using the same name would shadow one or the other. The alias makes the
    distinction explicit: DomainValidationError is ours, pydantic's is separate.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.requests import Request

from core.config import settings
from core.exceptions import (
    AssignmentConflictError,
    ConflictError,
    FoodNRepsError,
    ForbiddenError,
    InactiveUserError,
    NotFoundError,
    PlanVersionConflictError,
    SelfAssignmentError,
    StaffDomainViolationError,
    UnauthorizedError,
)
from core.exceptions import ValidationError as DomainValidationError
from infrastructure.db.session import AsyncSessionLocal, engine
from presentation.api.routes import (
    admin,
    auth,
    client,
    coach,
    comments,
    nutritionist,
    personal,
    trainer,
)
from presentation.api.routes.invites import router as invites_router

# ── Exception status map ──────────────────────────────────────────────────────

_STATUS_MAP: dict[type[FoodNRepsError], int] = {
    NotFoundError: 404,
    UnauthorizedError: 401,
    InactiveUserError: 401,
    ForbiddenError: 403,
    StaffDomainViolationError: 403,
    ConflictError: 409,
    AssignmentConflictError: 409,
    PlanVersionConflictError: 409,
    DomainValidationError: 422,
    SelfAssignmentError: 400,
}


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup: nothing to initialise (connection pool is lazy).
    Shutdown: dispose the engine to cleanly close all pool connections.
    """
    yield
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
)


# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,  # required for httpOnly cookie (refresh token)
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Domain exception handler ──────────────────────────────────────────────────


@app.exception_handler(FoodNRepsError)
async def domain_exception_handler(
    request: Request, exc: FoodNRepsError
) -> JSONResponse:
    """
    Translate every domain exception to the correct HTTP status code.

    Lookup order: exact type match first, then base classes via next().
    If a subclass is not in _STATUS_MAP, the base class match applies.
    FoodNRepsError itself (unmapped) → 400.
    """
    status = _STATUS_MAP.get(type(exc))
    if status is None:
        # Walk MRO to find the closest mapped parent class
        for klass in type(exc).__mro__:
            if klass in _STATUS_MAP:
                status = _STATUS_MAP[klass]
                break
        else:
            status = 400
    return JSONResponse(
        status_code=status,
        content={"detail": str(exc)},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(client.router, prefix="/client", tags=["Client"])
app.include_router(trainer.router, prefix="/trainer", tags=["Trainer"])
app.include_router(nutritionist.router, prefix="/nutritionist", tags=["Nutritionist"])
app.include_router(coach.router, prefix="/coach", tags=["Master Coach"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(personal.router, prefix="/personal", tags=["Personal Plans"])
app.include_router(invites_router, tags=["Invites"])
app.include_router(comments.router, prefix="/plans", tags=["Comments"])


# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/health", tags=["Health"], summary="Health check with DB connectivity")
async def health_check() -> dict[str, str]:
    """
    Active DB connectivity check — not just a static 200.
    Used by Docker HEALTHCHECK and future load balancer probes.
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
