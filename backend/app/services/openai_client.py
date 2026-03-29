import logging

from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class OpenAIClientFactory:
    """Factory for a shared AsyncOpenAI client (singleton per app lifecycle)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncOpenAI | None = None

    def get(self) -> AsyncOpenAI:
        if not self._settings.openai_api_key.strip():
            raise ConfigurationError("OPENAI_API_KEY is not set")
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._settings.openai_api_key)
            logger.debug("AsyncOpenAI client created")
        return self._client
