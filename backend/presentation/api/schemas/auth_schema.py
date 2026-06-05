"""
Auth request and response schemas.

Design choice — TokenResponse returns only the access token:
    The refresh token is an httpOnly cookie set directly on the response
    object in the route handler — it never appears in the JSON body. The
    client never sees the refresh token as a string; it is only ever sent
    back to /auth endpoints automatically by the browser. This prevents
    any application code from reading, storing, or logging the refresh token.
"""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
