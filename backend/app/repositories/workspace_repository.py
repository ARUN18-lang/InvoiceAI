from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.mongo_documents import COLLECTION_WORKSPACES


class WorkspaceRepository:
    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self._col = db[COLLECTION_WORKSPACES]

    async def list_all(self) -> list[dict[str, Any]]:
        cursor = self._col.find({}).sort("created_at", 1)
        return await cursor.to_list(length=500)

    async def create(self, name: str) -> ObjectId:
        now = datetime.now(timezone.utc)
        res = await self._col.insert_one({"name": name.strip(), "created_at": now})
        return res.inserted_id

    async def get(self, oid: ObjectId) -> dict[str, Any] | None:
        return await self._col.find_one({"_id": oid})
