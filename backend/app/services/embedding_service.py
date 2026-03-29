import logging

from openai import AsyncOpenAI

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, client: AsyncOpenAI, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def embed_text(self, text: str) -> list[float]:
        cleaned = text.replace("\n", " ").strip()[:8000]
        if not cleaned:
            return []
        response = await self._client.embeddings.create(
            model=self._settings.openai_embedding_model,
            input=cleaned,
        )
        return list(response.data[0].embedding)
