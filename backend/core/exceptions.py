"""
Food 'n' Reps — application exception hierarchy.

Design choice — domain exceptions, not HTTP exceptions:
    Services raise these. Routes catch them and translate to HTTP responses.
    This keeps business logic free of web framework concepts. A service that
    raises HTTPException(404) is coupled to FastAPI. A service that raises
    NotFoundError is not coupled to anything — it can be called from a CLI,
    a test, a background job, or a route with equal correctness.

Design choice — exception hierarchy rooted at FoodNRepsError:
    Catching `FoodNRepsError` in a route's exception handler covers every
    application-specific error in one handler, while still allowing specific
    subtypes to be caught individually where needed.

    try:
        return await service.do_something()
    except NotFoundError:
        raise HTTPException(404, detail=str(e))
    except ForbiddenError:
        raise HTTPException(403, detail=str(e))
    except FoodNRepsError:
        raise HTTPException(400, detail=str(e))  # catch-all for other domain errors

Sprint 4 registers a global exception handler in main.py that maps
each subtype to the correct HTTP status code automatically.
"""


# ── Base ──────────────────────────────────────────────────────────────────────

class FoodNRepsError(Exception):
    """Base class for all application-specific exceptions."""


# ── Standard HTTP-mappable errors ─────────────────────────────────────────────

class NotFoundError(FoodNRepsError):
    """
    A requested resource does not exist.
    Maps to HTTP 404.

    Usage: raise NotFoundError(f"Client {client_id} not found")
    """


class UnauthorizedError(FoodNRepsError):
    """
    The request has no valid authentication credentials.
    Maps to HTTP 401.

    Usage: raise UnauthorizedError("Access token is expired or invalid")
    """


class ForbiddenError(FoodNRepsError):
    """
    The authenticated user does not have permission for this action.
    Maps to HTTP 403.

    Usage: raise ForbiddenError("Fitness trainers cannot edit diet plans")
    """


class ConflictError(FoodNRepsError):
    """
    The request conflicts with the current state of a resource.
    Maps to HTTP 409.

    Used for: optimistic lock failures, duplicate resources.
    """


class ValidationError(FoodNRepsError):
    """
    Input data violates a business rule.
    Maps to HTTP 422.

    Distinct from Pydantic's ValidationError (which handles type/format).
    This handles business-level rules: "reps_min must be provided or reps_note".
    """


# ── Domain-specific conflicts ─────────────────────────────────────────────────

class AssignmentConflictError(ConflictError):
    """
    A staff assignment violates the coaching combination rules.

    Examples:
    - Assigning a master coach when a fitness trainer is already assigned.
    - Assigning a fitness trainer when a master coach is already assigned.

    Raised by: AssignmentService.assign_staff()
    """


class PlanVersionConflictError(ConflictError):
    """
    An optimistic lock conflict on a plan save.

    Raised when plan.version in the request does not match the current
    version in the database — meaning someone else saved a change between
    when this user loaded the plan and when they submitted their edit.

    Raised by: WorkoutProgramRepository.save(), DietPlanRepository.save()
    Message should include the current version so the client can reload.
    """


class StaffDomainViolationError(ForbiddenError):
    """
    A staff member attempted to act outside their domain ownership.

    Examples:
    - A fitness trainer attempting to write a diet plan entry.
    - A nutritionist attempting to write a workout prescription.

    Raised by: FitnessTrainerService, NutritionistService
    """


class SelfAssignmentError(FoodNRepsError):
    """
    A staff member attempted to assign themselves to a client.
    Maps to HTTP 400.
    """


class InactiveUserError(UnauthorizedError):
    """
    The authenticated user's account has been deactivated.
    Maps to HTTP 401 (not 403 — the user is not forbidden, they are inactive).
    """
