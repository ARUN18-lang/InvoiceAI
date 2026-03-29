from pathlib import Path

from app.core.exceptions import ExtractionError
from app.services.extraction.base import ExtractionResult, TextExtractor
from app.services.extraction.docling_extractor import DoclingExtractor
from app.services.extraction.unstructured_extractor import UnstructuredExtractor


class ExtractorFactory:
    """
    Chooses an extractor implementation (Chain-of-responsibility style).

    Preference: Docling for PDF when available; Unstructured as fallback and for images.
    """

    def __init__(self) -> None:
        self._extractors: list[TextExtractor] = [
            DoclingExtractor(),
            UnstructuredExtractor(),
        ]

    def extract(self, path: Path, mime_type: str) -> ExtractionResult:
        errors: list[str] = []
        for extractor in self._extractors:
            if not extractor.supports(path, mime_type):
                continue
            try:
                return extractor.extract(path, mime_type)
            except ExtractionError as e:
                errors.append(f"{extractor.name}: {e.message}")
                continue
        detail = "; ".join(errors) if errors else "no extractor matched"
        raise ExtractionError(f"Could not extract text ({detail})")
