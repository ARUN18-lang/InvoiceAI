from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, Response, UploadFile

from app.core.exceptions import AppError, ConfigurationError, ExtractionError, NotFoundError
from app.deps import WorkspaceOidDep, get_invoice_manager
from app.plugins.invoices.managers.invoice_manager import InvoiceManager
from app.schemas.invoice import InvoiceCreateResult, InvoiceRecord
from app.services.export_service import ExportService

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/upload", response_model=InvoiceCreateResult)
async def upload_invoice(
    background_tasks: BackgroundTasks,
    workspace_id: WorkspaceOidDep,
    file: UploadFile = File(...),
    manager: InvoiceManager = Depends(get_invoice_manager),
) -> InvoiceCreateResult:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    data = await file.read()
    if len(data) > manager.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds configured size limit")
    try:
        result, dest = await manager.start_upload(
            workspace_id=workspace_id,
            filename=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            data=data,
        )
        background_tasks.add_task(
            manager.run_processing_pipeline,
            workspace_id=workspace_id,
            invoice_id=result.invoice.id,
            dest=dest,
            mime_type=file.content_type or "application/octet-stream",
            filename=file.filename,
        )
        return result
    except ConfigurationError as e:
        raise HTTPException(status_code=503, detail=e.message) from e
    except ExtractionError as e:
        raise HTTPException(status_code=422, detail=e.message) from e
    except AppError as e:
        status = 413 if e.code == "payload_too_large" else 400
        raise HTTPException(status_code=status, detail=e.message) from e


@router.get("/export")
async def export_invoices(
    request: Request,
    workspace_id: WorkspaceOidDep,
    export_format: Literal["json", "csv", "xlsx"] = Query(..., alias="format"),
    limit: int = Query(default=2000, ge=1, le=5000),
) -> Response:
    db = request.app.state.mongo.database()
    svc = ExportService(db)
    if export_format == "json":
        body = await svc.as_json_bytes(workspace_id, limit)
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="invoices.json"'},
        )
    if export_format == "csv":
        body = await svc.as_csv_bytes(workspace_id, limit)
        return Response(
            content=body,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="invoices.csv"'},
        )
    body = await svc.as_xlsx_bytes(workspace_id, limit)
    return Response(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="invoices.xlsx"'},
    )


@router.get("/{invoice_id}", response_model=InvoiceRecord)
async def get_invoice(
    invoice_id: str,
    workspace_id: WorkspaceOidDep,
    manager: InvoiceManager = Depends(get_invoice_manager),
) -> InvoiceRecord:
    try:
        return await manager.get_invoice(invoice_id, workspace_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.get("", response_model=list[InvoiceRecord])
async def list_invoices(
    workspace_id: WorkspaceOidDep,
    limit: int = Query(default=50, ge=1, le=200),
    manager: InvoiceManager = Depends(get_invoice_manager),
) -> list[InvoiceRecord]:
    return await manager.list_invoices(workspace_id, limit)
