from datetime import datetime
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
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        await self.collection.insert_one(doc)
        return session

    async def get(self, session_id: str) -> Optional[CouncilSession]:
        """Get a session by ID."""
        doc = await self.collection.find_one({"id": session_id})
        if doc is None:
            return None
        return CouncilSession(**doc)

    async def update(self, session: CouncilSession) -> CouncilSession:
        """Update an existing session."""
        doc = session.model_dump()
        doc["updated_at"] = datetime.utcnow()
        await self.collection.update_one(
            {"id": session.id},
            {"$set": doc}
        )
        return session

    async def list_all(self, limit: int = 50) -> List[dict]:
        """List all sessions with basic info, ordered by most recent."""
        cursor = self.collection.find(
            {},
            {"id": 1, "question": 1, "status": 1, "created_at": 1, "_id": 0}
        ).sort("created_at", -1).limit(limit)

        sessions = []
        async for doc in cursor:
            sessions.append(doc)
        return sessions

    async def delete(self, session_id: str) -> bool:
        """Delete a session by ID."""
        result = await self.collection.delete_one({"id": session_id})
        return result.deleted_count > 0
