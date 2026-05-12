"""
FastAPI auth dependency.

`get_current_user` extracts the Bearer token from the Authorization
header, asks Supabase to validate it, and returns a `CurrentUser` carrying
the user's id, email, and the raw access token (needed to mint an
RLS-aware DB client downstream).

Endpoints that touch user-owned data should depend on this:

    @app.get("/api/chats")
    async def list_chats(user: CurrentUser = Depends(get_current_user)): ...

Failures (missing/invalid/expired token) raise 401.
"""

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .supabase_client import supabase_client


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: Optional[str]
    access_token: str


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # The anon client is enough to validate a JWT — get_user() hits
        # Supabase's GoTrue /user endpoint with the token in the header.
        anon = supabase_client.get_client()
        user_resp = anon.auth.get_user(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_obj = getattr(user_resp, "user", None)
    if user_obj is None or not getattr(user_obj, "id", None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        id=str(user_obj.id),
        email=getattr(user_obj, "email", None),
        access_token=token,
    )
