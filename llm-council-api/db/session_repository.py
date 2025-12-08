from datetime import datetime, timezone
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from schemas import CouncilSession


class SessionRepository:
    """Repository for session persistence in MongoDB."""

    COLLECTION_NAME = "sessions"

    def __init__(self, database: AsyncIOMotorDatabase):
        self.collection = database[self.COLLECTION_NAME]

    async def create(self, session: CouncilSession) -> CouncilSession:
        """Create a new session in the database."""
        doc = session.model_dump()
        doc["created_at"] = datetime.now(timezone.utc)
        doc["updated_at"] = datetime.now(timezone.utc)
        await self.collection.insert_one(doc)
        return session

    async def get(self, session_id: str, include_deleted: bool = False) -> Optional[CouncilSession]:
        """Get a session by ID."""
        query = {"id": session_id}
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}

        doc = await self.collection.find_one(query)
        if doc is None:
            return None
        return CouncilSession(**doc)

    async def update(self, session: CouncilSession) -> CouncilSession:
        """Update an existing session."""
        doc = session.model_dump()
        doc["updated_at"] = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"id": session.id},
            {"$set": doc}
        )
        return session

    async def list_all(self, limit: int = 50, include_deleted: bool = False) -> List[dict]:
        """List all sessions with basic info, ordered by most recent.

        Uses aggregation to avoid loading full rounds data - only extracts
        first question, last status, and round count for efficiency.
        """
        match_stage = {}
        if not include_deleted:
            match_stage["is_deleted"] = {"$ne": True}

        pipeline = [
            {"$match": match_stage},
            {"$sort": {"created_at": -1}},
            {"$limit": limit},
            {"$project": {
                "_id": 0,
                "id": 1,
                "title": 1,
                "created_at": 1,
                "is_pinned": {"$ifNull": ["$is_pinned", False]},
                # Extract only what we need from rounds array
                "question": {"$ifNull": [{"$arrayElemAt": ["$rounds.question", 0]}, ""]},
                "status": {"$ifNull": [{"$arrayElemAt": ["$rounds.status", -1]}, "pending"]},
                "round_count": {"$size": {"$ifNull": ["$rounds", []]}}
            }}
        ]

        sessions = []
        async for doc in self.collection.aggregate(pipeline):
            sessions.append(doc)
        return sessions

    async def soft_delete(self, session_id: str) -> bool:
        """Soft delete a session by ID."""
        now = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"id": session_id, "is_deleted": {"$ne": True}},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": now.isoformat(),
                    "updated_at": now
                }
            }
        )
        return result.modified_count > 0

    async def restore(self, session_id: str) -> bool:
        """Restore a soft-deleted session."""
        result = await self.collection.update_one(
            {"id": session_id, "is_deleted": True},
            {
                "$set": {
                    "is_deleted": False,
                    "deleted_at": None,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0

    async def hard_delete(self, session_id: str) -> bool:
        """Permanently delete a session by ID."""
        result = await self.collection.delete_one({"id": session_id})
        return result.deleted_count > 0

    async def get_by_share_token(self, share_token: str) -> Optional[CouncilSession]:
        """Get a shared session by its share token."""
        doc = await self.collection.find_one({
            "share_token": share_token,
            "is_shared": True,
            "is_deleted": {"$ne": True}
        })
        if doc is None:
            return None
        return CouncilSession(**doc)

    async def soft_delete_all(self, include_pinned: bool = False) -> int:
        """
        Soft delete all sessions.
        Returns the count of deleted sessions.

        Args:
            include_pinned: If True, also delete pinned sessions. Default False (preserve pinned).
        """
        now = datetime.now(timezone.utc)
        query = {"is_deleted": {"$ne": True}}

        if not include_pinned:
            query["is_pinned"] = {"$ne": True}

        result = await self.collection.update_many(
            query,
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": now.isoformat(),
                    "updated_at": now
                }
            }
        )
        return result.modified_count

    async def get_all_full(
        self,
        include_deleted: bool = False,
        limit: int = 1000,
        batch_size: int = 100
    ) -> List[CouncilSession]:
        """
        Get all sessions with full data (for export).
        Returns complete session objects including all rounds and responses.

        Args:
            include_deleted: Include soft-deleted sessions
            limit: Maximum number of sessions to return (default 1000, prevents memory issues)
            batch_size: MongoDB cursor batch size for efficient fetching
        """
        query = {}
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}

        sessions = []
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit).batch_size(batch_size)

        async for doc in cursor:
            sessions.append(CouncilSession(**doc))

        return sessions
