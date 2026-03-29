from datetime import date, datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument
from fastapi import APIRouter, HTTPException, Query, Request

from app.deps import WorkspaceOidDep
from app.schemas.mongo_documents import COLLECTION_NOTIFICATIONS
from app.schemas.notifications import NotificationRecord

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _as_date(v: datetime | date | None) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).date()
    return v


@router.get("", response_model=list[NotificationRecord])
async def list_notifications(
    request: Request,
    workspace_id: WorkspaceOidDep,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[NotificationRecord]:
    db = request.app.state.mongo.database()
    col = db[COLLECTION_NOTIFICATIONS]
    cursor = col.find({"workspace_id": workspace_id}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    out: list[NotificationRecord] = []
    for d in docs:
        created = d.get("created_at") or datetime.now(timezone.utc)
        if not isinstance(created, datetime):
            created = datetime.now(timezone.utc)
        raw_kind = d.get("kind", "due_soon")
        kind = raw_kind if raw_kind in ("due_soon", "overdue") else "due_soon"
        out.append(
            NotificationRecord(
                id=str(d["_id"]),
                kind=kind,
                invoice_id=d.get("invoice_id", ""),
                vendor_name=d.get("vendor_name"),
                due_date=_as_date(d.get("due_date")),
                message=d.get("message", ""),
                created_at=created,
                read=bool(d.get("read", False)),
            )
        )
    return out


@router.patch("/{notification_id}/read", response_model=NotificationRecord)
async def mark_notification_read(
    notification_id: str,
    request: Request,
    workspace_id: WorkspaceOidDep,
) -> NotificationRecord:
    try:
        oid = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid notification id") from None
    db = request.app.state.mongo.database()
    col = db[COLLECTION_NOTIFICATIONS]
    res = await col.find_one_and_update(
        {"_id": oid, "workspace_id": workspace_id},
        {"$set": {"read": True}},
        return_document=ReturnDocument.AFTER,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Notification not found")
    created = res.get("created_at") or datetime.now(timezone.utc)
    if not isinstance(created, datetime):
        created = datetime.now(timezone.utc)
    rk = res.get("kind", "due_soon")
    rk2 = rk if rk in ("due_soon", "overdue") else "due_soon"
    return NotificationRecord(
        id=str(res["_id"]),
        kind=rk2,
        invoice_id=res.get("invoice_id", ""),
        vendor_name=res.get("vendor_name"),
        due_date=_as_date(res.get("due_date")),
        message=res.get("message", ""),
        created_at=created,
        read=True,
    )
