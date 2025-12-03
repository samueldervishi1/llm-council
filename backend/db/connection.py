import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from config import settings

logger = logging.getLogger("llm-council.db")

_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None
_indexes_created: bool = False


async def get_database() -> AsyncIOMotorDatabase:
    """Get the MongoDB database instance."""
    global _client, _database

    if _database is None:
        _client = AsyncIOMotorClient(settings.mongodb_url)
        _database = _client[settings.mongodb_database]

    return _database


async def ensure_indexes(database: AsyncIOMotorDatabase) -> None:
    """Create indexes for optimal query performance."""
    global _indexes_created

    if _indexes_created:
        return

    sessions_collection = database["sessions"]

    try:
        # Index for session lookup by ID (most common query)
        await sessions_collection.create_index(
            [("id", ASCENDING)],
            unique=True,
            name="idx_session_id"
        )

        # Index for shared session lookup by token
        await sessions_collection.create_index(
            [("share_token", ASCENDING)],
            sparse=True,  # Only index documents with share_token
            name="idx_share_token"
        )

        # Compound index for listing sessions (filtered by is_deleted, sorted by created_at)
        await sessions_collection.create_index(
            [("is_deleted", ASCENDING), ("created_at", DESCENDING)],
            name="idx_list_sessions"
        )

        # Index for pinned sessions
        await sessions_collection.create_index(
            [("is_pinned", ASCENDING), ("pinned_at", DESCENDING)],
            sparse=True,
            name="idx_pinned_sessions"
        )

        _indexes_created = True
        logger.info("MongoDB indexes created successfully")

    except Exception as e:
        logger.warning(f"Failed to create indexes (may already exist): {e}")
        _indexes_created = True  # Don't retry on every request


async def close_database() -> None:
    """Close the MongoDB connection."""
    global _client, _database, _indexes_created

    if _client is not None:
        _client.close()
        _client = None
        _database = None
        _indexes_created = False
