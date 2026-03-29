import logging
from typing import Any, AsyncIterator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import Settings
from app.schemas.mongo_documents import COLLECTION_NOTIFICATIONS, COLLECTION_WORKSPACES

logger = logging.getLogger(__name__)


class MongoManager:
    """Lifecycle manager for a single Motor client (connection pool)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncIOMotorClient[Any] | None = None

    async def connect(self) -> None:
        if self._client is not None:
            return
        self._client = AsyncIOMotorClient(self._settings.mongodb_uri)
        await self._client.admin.command("ping")
        logger.info("MongoDB connected")

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("MongoDB disconnected")

    def database(self) -> AsyncIOMotorDatabase[Any]:
        if self._client is None:
            raise RuntimeError("MongoManager is not connected")
        return self._client[self._settings.mongodb_db]


async def ensure_workspaces_and_migration(db: AsyncIOMotorDatabase[Any]) -> None:
    from datetime import datetime, timezone

    ws_col = db[COLLECTION_WORKSPACES]
    invoices = db["invoices"]
    if await ws_col.count_documents({}) == 0:
        await ws_col.insert_one({"name": "Default", "created_at": datetime.now(timezone.utc)})
    first = await ws_col.find_one(sort=[("created_at", 1)])
    if first:
        wid = first["_id"]
        await invoices.update_many({"workspace_id": {"$exists": False}}, {"$set": {"workspace_id": wid}})
    await ws_col.create_index([("created_at", 1)])


async def ensure_indexes(db: AsyncIOMotorDatabase[Any]) -> None:
    """Create indexes matching the documented Mongo schema."""
    await ensure_workspaces_and_migration(db)
    invoices = db["invoices"]
    await invoices.create_index([("created_at", -1)])
    await invoices.create_index([("vendor_normalized", 1), ("invoice_number", 1)])
    await invoices.create_index([("invoice_date", -1)])
    await invoices.create_index([("due_date", 1)])
    await invoices.create_index([("category", 1)])
    await invoices.create_index([("workspace_id", 1), ("created_at", -1)])
    await invoices.create_index([("workspace_id", 1), ("vendor_normalized", 1), ("invoice_number", 1)])
    notes = db[COLLECTION_NOTIFICATIONS]
    await notes.create_index([("created_at", -1)])
    await notes.create_index([("invoice_id", 1), ("kind", 1), ("day_key", 1)])
    await notes.create_index([("workspace_id", 1), ("created_at", -1)])
    # Vector search: define Atlas search index on `embedding` when using ATLAS_VECTOR_INDEX_NAME
    logger.info("MongoDB indexes ensured")


class MongoProvider:
    """Provides database handle; use with FastAPI lifespan."""

    def __init__(self, manager: MongoManager) -> None:
        self._manager = manager

    def get(self) -> AsyncIOMotorDatabase[Any]:
        return self._manager.database()


async def mongo_lifecycle(settings: Settings) -> AsyncIterator[MongoManager]:
    manager = MongoManager(settings)
    await manager.connect()
    await ensure_indexes(manager.database())
    try:
        yield manager
    finally:
        await manager.disconnect()
