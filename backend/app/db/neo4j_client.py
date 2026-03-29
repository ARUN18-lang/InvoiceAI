import logging
from typing import Any, AsyncIterator, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from app.core.config import Settings

logger = logging.getLogger(__name__)


class Neo4jManager:
    """Optional Neo4j driver for graph-backed RAG and relationship queries."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver: Optional[AsyncDriver] = None

    @property
    def enabled(self) -> bool:
        return self._settings.neo4j_enabled

    async def connect(self) -> None:
        if not self.enabled:
            return
        self._driver = AsyncGraphDatabase.driver(
            self._settings.neo4j_uri,
            auth=(self._settings.neo4j_user, self._settings.neo4j_password),
        )
        await self._driver.verify_connectivity()
        logger.info("Neo4j connected")

    async def disconnect(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j disconnected")

    def session(self) -> AsyncSession:
        if self._driver is None:
            raise RuntimeError("Neo4j is not configured or not connected")
        return self._driver.session()


async def neo4j_lifecycle(settings: Settings) -> AsyncIterator[Neo4jManager]:
    manager = Neo4jManager(settings)
    await manager.connect()
    try:
        yield manager
    finally:
        await manager.disconnect()


async def ensure_graph_constraints(session: AsyncSession) -> None:
    """Idempotent constraints for invoice graph model."""
    await session.run(
        """
        CREATE CONSTRAINT invoice_id IF NOT EXISTS
        FOR (i:Invoice) REQUIRE i.mongo_id IS UNIQUE
        """
    )
    await session.run(
        """
        CREATE CONSTRAINT vendor_key IF NOT EXISTS
        FOR (v:Vendor) REQUIRE v.key IS UNIQUE
        """
    )
    await session.run(
        """
        CREATE CONSTRAINT category_name IF NOT EXISTS
        FOR (c:Category) REQUIRE c.name IS UNIQUE
        """
    )
