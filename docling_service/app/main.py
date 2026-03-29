"""
Standalone Docling conversion API: accepts file uploads, runs conversion in a
thread pool so multiple PDFs can be processed concurrently.
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Header, HTTPException, UploadFile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORKERS = max(1, int(os.environ.get("DOCLING_WORKERS", "2")))
API_KEY = os.environ.get("DOCLING_API_KEY", "").strip()

JOBS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="docling")


def _convert_to_markdown(path: Path) -> str:
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(str(path))
    return result.document.export_to_markdown()


def _run_job(job_id: str, file_path: Path) -> None:
    try:
        with _LOCK:
            if job_id in JOBS:
                JOBS[job_id]["status"] = "processing"
        text = _convert_to_markdown(file_path)
        text = (text or "").strip()
        with _LOCK:
            if job_id in JOBS:
                JOBS[job_id]["status"] = "completed"
                JOBS[job_id]["markdown"] = text
                JOBS[job_id]["error"] = None
    except Exception as e:
        logger.exception("Job %s failed", job_id)
        with _LOCK:
            if job_id in JOBS:
                JOBS[job_id]["status"] = "failed"
                JOBS[job_id]["error"] = str(e)
                JOBS[job_id]["markdown"] = None
    finally:
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            pass


def _check_api_key(x_api_key: str | None) -> None:
    if not API_KEY:
        return
    if (x_api_key or "").strip() != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


app = FastAPI(title="Docling conversion service", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "workers": WORKERS}


@app.post("/v1/jobs")
async def create_job(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, str]:
    _check_api_key(x_api_key)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    job_id = uuid.uuid4().hex
    tmp_dir = Path(os.environ.get("DOCLING_TMP", os.path.join(os.getcwd(), ".docling_tmp")))
    tmp_dir.mkdir(parents=True, exist_ok=True)
    safe = file.filename.replace("/", "_").replace("\\", "_")
    file_path = tmp_dir / f"{job_id}_{safe}"
    file_path.write_bytes(data)

    with _LOCK:
        JOBS[job_id] = {
            "status": "queued",
            "markdown": None,
            "error": None,
        }

    _executor.submit(_run_job, job_id, file_path)
    logger.info("Queued job %s (%s bytes)", job_id, len(data))
    return {"job_id": job_id}


@app.get("/v1/jobs/{job_id}")
async def get_job(
    job_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    with _LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return {
        "job_id": job_id,
        "status": job["status"],
        "markdown": job.get("markdown"),
        "error": job.get("error"),
    }
