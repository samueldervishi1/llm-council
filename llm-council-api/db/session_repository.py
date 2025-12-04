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
        """List all sessions with basic info, ordered by most recent."""
        query = {}
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}

        cursor = self.collection.find(
            query,
            {"id": 1, "title": 1, "rounds": 1, "created_at": 1, "is_pinned": 1, "pinned_at": 1, "_id": 0}
        ).sort("created_at", -1).limit(limit)

        sessions = []
        async for doc in cursor:
            # Extract first question and last round status for summary
            rounds = doc.get("rounds", [])
            first_question = rounds[0]["question"] if rounds else ""
            last_status = rounds[-1]["status"] if rounds else "pending"

            sessions.append({
                "id": doc["id"],
                "title": doc.get("title"),
                "question": first_question,
                "status": last_status,
                "round_count": len(rounds),
                "created_at": doc.get("created_at"),
                "is_pinned": doc.get("is_pinned", False)
            })
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

    async def get_all_full(self, include_deleted: bool = False) -> List[CouncilSession]:
        """
        Get all sessions with full data (for export).
        Returns complete session objects including all rounds and responses.
        """
        query = {}
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}

        sessions = []
        cursor = self.collection.find(query).sort("created_at", -1)

        async for doc in cursor:
            sessions.append(CouncilSession(**doc))

        return sessions
