from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.schemas.invoice import ChatRequest, ChatResponse
from app.services.graph_sync_service import GraphSyncService
from app.services.openai_client import OpenAIClientFactory
from app.services.rag_service import InvoiceRAGService


class ChatManager:
    def __init__(
        self,
        *,
        db: AsyncIOMotorDatabase,
        settings: Settings,
        openai_factory: OpenAIClientFactory,
        graph: GraphSyncService,
    ) -> None:
        self._db = db
        self._settings = settings
        self._openai_factory = openai_factory
        self._graph = graph

    async def ask(self, body: ChatRequest, *, workspace_id: ObjectId) -> ChatResponse:
        client = self._openai_factory.get()
        rag = InvoiceRAGService(self._db, client, self._settings, self._graph)
        return await rag.answer(body, workspace_id=workspace_id)
