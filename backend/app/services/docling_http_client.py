from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import httpx

from app.core.config import Settings
from app.core.exceptions import ExtractionError

logger = logging.getLogger(__name__)


class DoclingHttpClient:
    """Submit files to the Docling microservice and poll until markdown is ready."""

    def __init__(self, settings: Settings) -> None:
        self._base = settings.docling_service_url.strip().rstrip("/")
        self._api_key = settings.docling_service_api_key.strip()
        self._poll = max(0.3, float(settings.docling_poll_interval_sec))
        self._timeout = max(30, int(settings.docling_job_timeout_sec))

    @property
    def enabled(self) -> bool:
        return bool(self._base)

    async def convert_to_markdown(self, file_path: Path, mime_type: str, original_filename: str) -> str:
        if not self.enabled:
            raise ExtractionError("Docling service URL is not configured")

        headers: dict[str, str] = {}
        if self._api_key:
            headers["X-API-Key"] = self._api_key

        content = file_path.read_bytes()
        name = original_filename or file_path.name

        timeout = httpx.Timeout(self._timeout + 30.0, connect=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            files = {"file": (name, content, mime_type or "application/octet-stream")}
            resp = await client.post(f"{self._base}/v1/jobs", files=files, headers=headers)
            if resp.status_code >= 400:
                raise ExtractionError(f"Docling service rejected upload: {resp.text[:500]}")
            job_id = resp.json().get("job_id")
            if not job_id:
                raise ExtractionError("Docling service returned no job_id")

            deadline = time.monotonic() + float(self._timeout)
            while time.monotonic() < deadline:
                await asyncio.sleep(self._poll)
                jr = await client.get(f"{self._base}/v1/jobs/{job_id}", headers=headers)
                if jr.status_code >= 400:
                    raise ExtractionError(f"Docling job status error: {jr.text[:500]}")
                data = jr.json()
                status = data.get("status")
                if status == "completed":
                    text = (data.get("markdown") or "").strip()
                    if not text:
                        raise ExtractionError("Docling returned empty markdown")
                    return text
                if status == "failed":
                    err = data.get("error") or "unknown error"
                    raise ExtractionError(f"Docling job failed: {err}")

            raise ExtractionError("Docling job timed out")
