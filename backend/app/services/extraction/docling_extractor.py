import logging
from pathlib import Path

from app.core.exceptions import ExtractionError
from app.services.extraction.base import ExtractionResult, TextExtractor

logger = logging.getLogger(__name__)


class DoclingExtractor(TextExtractor):
    name = "docling"

    def supports(self, path: Path, mime_type: str) -> bool:
        suffix = path.suffix.lower()
        return mime_type == "application/pdf" or suffix == ".pdf"

    def extract(self, path: Path, mime_type: str) -> ExtractionResult:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as e:
            raise ExtractionError("docling is not installed or failed to import") from e

        try:
            converter = DocumentConverter()
            result = converter.convert(str(path))
            text = result.document.export_to_markdown()
        except Exception as e:
            logger.exception("Docling extraction failed")
            raise ExtractionError(f"Docling failed: {e}") from e

        if not text or not text.strip():
            raise ExtractionError("Docling returned empty text")
        return ExtractionResult(text=text.strip(), backend=self.name)
