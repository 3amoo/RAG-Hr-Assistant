import hmac

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from helpers.config import get_settings


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
    settings=Depends(get_settings),
) -> str | None:
    """Validate the shared X-API-Key header.

    An empty API_KEY setting intentionally disables auth for trusted local
    development. Configure a non-empty key before any network exposure.
    """
    if not settings.API_KEY:
        return None

    if api_key is None or not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )

    return api_key
