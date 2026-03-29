from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="OPENAI_EMBEDDING_MODEL",
    )

    mongodb_uri: str = Field(default="mongodb://localhost:27017", validation_alias="MONGODB_URI")
    mongodb_db: str = Field(default="smart_invoice", validation_alias="MONGODB_DB")

    neo4j_uri: str = Field(default="", validation_alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    neo4j_password: str = Field(default="", validation_alias="NEO4J_PASSWORD")

    api_prefix: str = Field(default="/api/v1", validation_alias="API_PREFIX")
    upload_dir: Path = Field(default=Path("./data/uploads"), validation_alias="UPLOAD_DIR")
    max_upload_mb: int = Field(default=25, validation_alias="MAX_UPLOAD_MB")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="CORS_ORIGINS",
        description="Comma-separated list of allowed browser origins",
    )

    docling_service_url: str = Field(
        default="",
        validation_alias="DOCLING_SERVICE_URL",
        description="Base URL of the standalone Docling service (e.g. http://127.0.0.1:8765). Empty = local extractors only.",
    )
    docling_service_api_key: str = Field(default="", validation_alias="DOCLING_SERVICE_API_KEY")
    docling_poll_interval_sec: float = Field(default=1.5, validation_alias="DOCLING_POLL_INTERVAL_SEC")
    docling_job_timeout_sec: int = Field(default=900, validation_alias="DOCLING_JOB_TIMEOUT_SEC")

    # MongoDB Atlas Vector Search (optional). When set, RAG uses $vectorSearch on `embedding`.
    atlas_vector_index_name: str = Field(default="", validation_alias="ATLAS_VECTOR_INDEX_NAME")
    atlas_vector_num_candidates: int = Field(default=150, validation_alias="ATLAS_VECTOR_NUM_CANDIDATES")

    # Due-date scheduler + optional webhook for new alerts
    scheduler_enabled: bool = Field(default=True, validation_alias="SCHEDULER_ENABLED")
    due_alert_days_ahead: int = Field(default=7, validation_alias="DUE_ALERT_DAYS_AHEAD")
    alert_webhook_url: str = Field(default="", validation_alias="ALERT_WEBHOOK_URL")

    @property
    def neo4j_enabled(self) -> bool:
        return bool(self.neo4j_uri.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
