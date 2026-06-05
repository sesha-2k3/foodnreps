"""
Authentication routes: login, refresh, logout.

No authentication guard on any route here — these routes ARE the mechanism
for establishing or ending authentication. Login and refresh prove identity;
requiring prior identity proof to prove identity is circular.

Design choice — cookie helper function, not a separate middleware:
    _set_refresh_cookie and _clear_refresh_cookie are module-level helpers
    called explicitly from the route handlers. An alternative is middleware
    that inspects the response body and sets cookies automatically. The
    explicit call is clearer — the cookie is set exactly where and when the
    route intends it, not invisibly in middleware.

Design choice — logout returns 204 No Content even if no cookie:
    If the browser presents no refresh token cookie (e.g., already cleared),
    logout still returns 204. The caller's intent (end this session) is
    accomplished. Raising a 401 for missing cookie on logout would mean a
    partially logged-out user could never complete the logout.
"""

from fastapi import APIRouter, Depends, Request, Response

from application.services.auth_service import AuthService
from core.config import settings
from presentation.api.dependencies import get_auth_service
from presentation.api.schemas.auth_schema import LoginRequest, TokenResponse

router = APIRouter()


# ── Cookie helpers ────────────────────────────────────────────────────────────


def _set_refresh_cookie(response: Response, token: str) -> None:
    """
    Set the httpOnly refresh token cookie on the response.

    path="/auth" — browser only sends this cookie to /auth/* endpoints.
    samesite="lax" — blocks cross-site AJAX (CSRF vector) while allowing
                     top-level navigations (needed for page-load refresh).
    secure — True in production (HTTPS only), False in development.
    max_age — seconds until the cookie expires, matching the JWT expiry.
    """
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        path="/auth",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="refresh_token", path="/auth")


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive an access token + refresh cookie",
)
async def login(
    body: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Verify email/password and return a short-lived access token in the
    response body. A long-lived refresh token is set as an httpOnly cookie.

    The access token must be stored in JS memory and sent as a Bearer header.
    The refresh cookie is sent automatically by the browser to /auth endpoints.
    """
    access_token, refresh_token = await auth_service.login(body.email, body.password)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a valid refresh cookie for a new access token",
)
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Validate the httpOnly refresh token cookie, rotate it (old is revoked,
    new one issued), and return a new access token in the response body.

    The browser sends the cookie automatically because the request path
    begins with /auth.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        from core.exceptions import UnauthorizedError

        raise UnauthorizedError("No refresh token cookie found. Please log in again.")
    new_access, new_refresh = await auth_service.refresh(refresh_token)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=new_access)


@router.post(
    "/logout",
    status_code=204,
    summary="Revoke the refresh token and clear the cookie",
)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """
    Revoke the refresh token in the database and delete the cookie.
    Returns 204 whether or not a cookie was present — logout is idempotent.
    """
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await auth_service.logout(refresh_token)
    _clear_refresh_cookie(response)
