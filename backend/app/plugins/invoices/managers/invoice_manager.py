import asyncio
import logging
import uuid
from pathlib import Path

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.core.exceptions import AppError, ConfigurationError, ExtractionError
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.invoice import InvoiceCreateResult, InvoiceRecord
from app.services.docling_http_client import DoclingHttpClient
from app.services.embedding_service import EmbeddingService
from app.services.extraction.factory import ExtractorFactory
from app.services.graph_sync_service import GraphSyncService
from app.services.invoice_llm_service import InvoiceLLMService
from app.services.openai_client import OpenAIClientFactory
from app.services.validation_service import InvoiceValidationService

logger = logging.getLogger(__name__)


class InvoiceManager:
    """Application service orchestrating upload → extract → LLM → validate → persist → graph."""

    def __init__(
        self,
        *,
        db: AsyncIOMotorDatabase,
        settings: Settings,
        openai_factory: OpenAIClientFactory,
        neo4j_graph: GraphSyncService,
    ) -> None:
        self._db = db
        self._settings = settings
        self._openai_factory = openai_factory
        self._extractors = ExtractorFactory()
        self._repo = InvoiceRepository(db)
        self._graph = neo4j_graph
        self._docling_http = DoclingHttpClient(settings)

    @property
    def max_upload_bytes(self) -> int:
        return self._settings.max_upload_mb * 1024 * 1024

    def _ensure_upload_dir(self) -> Path:
        path = Path(self._settings.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _is_pdf(self, path: Path, mime_type: str) -> bool:
        return mime_type == "application/pdf" or path.suffix.lower() == ".pdf"

    def _extract_sync(self, dest: Path, mime_type: str) -> tuple[str, str]:
        extraction = self._extractors.extract(dest, mime_type)
        return extraction.text.strip(), extraction.backend

    async def _extract_text(self, dest: Path, mime_type: str, original_filename: str) -> tuple[str, str]:
        if self._docling_http.enabled and self._is_pdf(dest, mime_type):
            try:
                text = await self._docling_http.convert_to_markdown(dest, mime_type, original_filename)
                return text, "docling"
            except ExtractionError as e:
                logger.warning("Docling service failed (%s); falling back to local extractors", e.message)

        return await asyncio.to_thread(self._extract_sync, dest, mime_type)

    async def start_upload(
        self,
        *,
        workspace_id: ObjectId,
        filename: str,
        mime_type: str,
        data: bytes,
    ) -> tuple[InvoiceCreateResult, Path]:
        if not self._settings.openai_api_key.strip():
            raise ConfigurationError("OPENAI_API_KEY is required for digitization")
        if len(data) > self.max_upload_bytes:
            raise AppError("File exceeds configured size limit", code="payload_too_large")

        upload_root = self._ensure_upload_dir()
        safe_name = filename.replace("/", "_").replace("\\", "_")
        unique = f"{uuid.uuid4().hex}_{safe_name}"
        dest = upload_root / unique
        dest.write_bytes(data)

        invoice_id = await self._repo.insert_processing_placeholder(
            workspace_id=workspace_id,
            storage_path=str(dest),
            original_filename=filename,
            mime_type=mime_type,
        )
        record = await self._repo.get(invoice_id, workspace_id)
        return (
            InvoiceCreateResult(invoice=record, extraction_backend=None, raw_text_length=None),
            dest,
        )

    async def run_processing_pipeline(
        self,
        *,
        workspace_id: ObjectId,
        invoice_id: str,
        dest: Path,
        mime_type: str,
        filename: str,
    ) -> None:
        try:
            if not self._settings.openai_api_key.strip():
                await self._repo.mark_failed(
                    invoice_id, workspace_id, "OPENAI_API_KEY is required for digitization"
                )
                return

            try:
                text, backend = await self._extract_text(dest, mime_type, filename)
            except ExtractionError as e:
                await self._repo.mark_failed(invoice_id, workspace_id, e.message)
                return
            except AppError as e:
                await self._repo.mark_failed(invoice_id, workspace_id, e.message)
                return

            if not text:
                await self._repo.mark_failed(invoice_id, workspace_id, "Extraction returned empty text")
                return

            client = self._openai_factory.get()
            llm = InvoiceLLMService(client, self._settings)
            parsed = await llm.parse_from_text(text)

            validator = InvoiceValidationService(self._db)
            try:
                excl = ObjectId(invoice_id)
            except Exception:
                excl = None
            validation = await validator.validate(parsed, exclude_id=excl, workspace_id=workspace_id)

            embedder = EmbeddingService(client, self._settings)
            embed_input = (
                f"{parsed.vendor_name or ''} {parsed.invoice_number or ''} "
                f"{parsed.expense_category or ''} {text[:6000]}"
            )
            embedding = await embedder.embed_text(embed_input)

            await self._repo.complete_processing(
                invoice_id,
                workspace_id,
                parsed=parsed,
                validation=validation,
                embedding=embedding,
                extraction_backend=backend,
                raw_text=text,
            )
            await self._graph.upsert_invoice_graph(invoice_id, parsed, parsed.expense_category)
        except Exception as e:
            logger.exception("Pipeline failed for invoice %s", invoice_id)
            await self._repo.mark_failed(invoice_id, workspace_id, str(e))

    async def process_upload(
        self,
        *,
        workspace_id: ObjectId,
        filename: str,
        mime_type: str,
        data: bytes,
    ) -> InvoiceCreateResult:
        """Run the full pipeline in-process (blocks until finished)."""
        result, dest = await self.start_upload(
            workspace_id=workspace_id, filename=filename, mime_type=mime_type, data=data
        )
        await self.run_processing_pipeline(
            workspace_id=workspace_id,
            invoice_id=result.invoice.id,
            dest=dest,
            mime_type=mime_type,
            filename=filename,
        )
        record = await self._repo.get(result.invoice.id, workspace_id)
        backend, text_len = await self._repo.get_extraction_meta(result.invoice.id, workspace_id)
        return InvoiceCreateResult(invoice=record, extraction_backend=backend, raw_text_length=text_len)

    async def get_invoice(self, invoice_id: str, workspace_id: ObjectId) -> InvoiceRecord:
        return await self._repo.get(invoice_id, workspace_id)

    async def list_invoices(self, workspace_id: ObjectId, limit: int = 50) -> list[InvoiceRecord]:
        return await self._repo.list_recent(workspace_id, limit)
