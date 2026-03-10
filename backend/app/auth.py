import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "")

_bearer = HTTPBearer()


def require_api_key(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """Validate Bearer token against GATEWAY_API_KEY.

    If GATEWAY_API_KEY is not set (empty), authentication is disabled
    and all requests are allowed (backwards-compatible with MVP).
    """
    if not GATEWAY_API_KEY:
        return ""
    if creds.credentials != GATEWAY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return creds.credentials
