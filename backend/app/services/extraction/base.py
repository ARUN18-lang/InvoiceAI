from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    backend: str


class TextExtractor(ABC):
    """Strategy: extract plain text from a file on disk."""

    name: str

    @abstractmethod
    def supports(self, path: Path, mime_type: str) -> bool:
        ...

    @abstractmethod
    def extract(self, path: Path, mime_type: str) -> ExtractionResult:
        ...
