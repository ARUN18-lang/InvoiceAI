from fastapi import APIRouter, Depends, HTTPException

from app.core.exceptions import ConfigurationError
from app.deps import WorkspaceOidDep, get_chat_manager
from app.plugins.chat.managers.chat_manager import ChatManager
from app.schemas.invoice import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/invoices", response_model=ChatResponse)
async def chat_over_invoices(
    body: ChatRequest,
    workspace_id: WorkspaceOidDep,
    manager: ChatManager = Depends(get_chat_manager),
) -> ChatResponse:
    try:
        return await manager.ask(body, workspace_id=workspace_id)
    except ConfigurationError as e:
        raise HTTPException(status_code=503, detail=e.message) from e
