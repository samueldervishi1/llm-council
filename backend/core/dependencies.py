from clients import OpenRouterClient
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
