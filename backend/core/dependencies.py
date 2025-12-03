import secrets
from typing import Optional

from fastapi import Header, HTTPException, Query, status

from clients import OpenRouterClient
from config import settings
from db import get_database, SessionRepository

# Singleton client instance
_openrouter_client: OpenRouterClient | None = None
_session_repository: SessionRepository | None = None


async def get_session_repository() -> SessionRepository:
    """Get the session repository dependency."""
    global _session_repository
    if _session_repository is None:
        database = await get_database()
        _session_repository = SessionRepository(database)
    return _session_repository


def get_openrouter_client() -> OpenRouterClient:
    """Get the OpenRouter client dependency."""
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenRouterClient()
    return _openrouter_client


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key: Optional[str] = Query(None, alias="api_key")
) -> bool:
    """
    Verify API key for protected endpoints.

    API key can be provided via:
    - X-API-Key header (recommended)
    - api_key query parameter (for testing)

    If no API key is configured in settings, authentication is disabled.
    """
    # If no API key is configured, allow all requests (development mode)
    if not settings.api_key:
        return True

    # Get the provided key from header or query param
    provided_key = x_api_key or api_key

    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header or api_key query parameter.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(provided_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return True
