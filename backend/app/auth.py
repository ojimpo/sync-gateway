import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# auto_error=False にして、未指定時も 401 で統一して返す
_bearer = HTTPBearer(auto_error=False)


def _current_api_key() -> str:
    """Read API key from environment at request time.

    This allows runtime env updates to be reflected without process-level constants.
    """
    return os.getenv("GATEWAY_API_KEY", "")


def require_api_key(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Validate Bearer token against GATEWAY_API_KEY.

    If GATEWAY_API_KEY is not set (empty), authentication is disabled
    and all requests are allowed (backwards-compatible with MVP).
    """
    configured = _current_api_key()
    if not configured:
        return ""

    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if creds.credentials != configured:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return creds.credentials
