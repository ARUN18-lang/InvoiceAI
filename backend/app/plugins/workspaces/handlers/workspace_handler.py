from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request

from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceRecord

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _to_record(doc: dict) -> WorkspaceRecord:
    created = doc.get("created_at") or datetime.now(timezone.utc)
    if not isinstance(created, datetime):
        created = datetime.now(timezone.utc)
    return WorkspaceRecord(id=str(doc["_id"]), name=doc.get("name", "Workspace"), created_at=created)


@router.get("", response_model=list[WorkspaceRecord])
async def list_workspaces(request: Request) -> list[WorkspaceRecord]:
    db = request.app.state.mongo.database()
    repo = WorkspaceRepository(db)
    docs = await repo.list_all()
    return [_to_record(d) for d in docs]


@router.post("", response_model=WorkspaceRecord)
async def create_workspace(body: WorkspaceCreate, request: Request) -> WorkspaceRecord:
    db = request.app.state.mongo.database()
    repo = WorkspaceRepository(db)
    oid = await repo.create(body.name)
    doc = await repo.get(oid)
    if not doc:
        raise HTTPException(status_code=500, detail="Workspace create failed")
    return _to_record(doc)


@router.get("/{workspace_id}", response_model=WorkspaceRecord)
async def get_workspace(workspace_id: str, request: Request) -> WorkspaceRecord:
    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workspace id") from None
    db = request.app.state.mongo.database()
    repo = WorkspaceRepository(db)
    doc = await repo.get(oid)
    if not doc:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return _to_record(doc)
