import logging
from pathlib import Path

from app.core.exceptions import ExtractionError
from app.services.extraction.base import ExtractionResult, TextExtractor

logger = logging.getLogger(__name__)


class UnstructuredExtractor(TextExtractor):
    name = "unstructured"

    def supports(self, path: Path, mime_type: str) -> bool:
        suffix = path.suffix.lower()
        allowed = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".heic"}
        if suffix in allowed:
            return True
        return mime_type.startswith("image/") or mime_type == "application/pdf"

    def extract(self, path: Path, mime_type: str) -> ExtractionResult:
        try:
            from unstructured.partition.auto import partition
        except ImportError as e:
            raise ExtractionError("unstructured is not installed or failed to import") from e

        try:
            elements = partition(filename=str(path))
            text = "\n\n".join(str(el) for el in elements)
        except Exception as e:
            logger.exception("Unstructured extraction failed")
            raise ExtractionError(f"Unstructured failed: {e}") from e

        if not text or not text.strip():
            raise ExtractionError("Unstructured returned empty text")
        return ExtractionResult(text=text.strip(), backend=self.name)
