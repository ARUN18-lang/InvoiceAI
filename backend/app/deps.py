from typing import Annotated

from bson import ObjectId
from fastapi import Depends, Header, HTTPException, Query, Request

from app.plugins.chat.managers.chat_manager import ChatManager
from app.plugins.invoices.managers.invoice_manager import InvoiceManager
from app.repositories.workspace_repository import WorkspaceRepository


def get_invoice_manager(request: Request) -> InvoiceManager:
    return request.app.state.invoice_manager


def get_chat_manager(request: Request) -> ChatManager:
    return request.app.state.chat_manager


async def require_workspace_oid(
    request: Request,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    workspace_id: str | None = Query(
        default=None,
        description="Optional; use when the client cannot set headers (e.g. file download links).",
    ),
) -> ObjectId:
    raw = (x_workspace_id or workspace_id or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="X-Workspace-Id header or workspace_id query is required")
    try:
        oid = ObjectId(raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid X-Workspace-Id") from e
    db = request.app.state.mongo.database()
    repo = WorkspaceRepository(db)
    if not await repo.get(oid):
        raise HTTPException(status_code=404, detail="Workspace not found")
    return oid


InvoiceManagerDep = Annotated[InvoiceManager, Depends(get_invoice_manager)]
ChatManagerDep = Annotated[ChatManager, Depends(get_chat_manager)]
WorkspaceOidDep = Annotated[ObjectId, Depends(require_workspace_oid)]
