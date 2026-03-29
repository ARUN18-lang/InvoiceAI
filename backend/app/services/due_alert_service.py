from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.mongo_documents import COLLECTION_INVOICES, COLLECTION_NOTIFICATIONS

logger = logging.getLogger(__name__)


def _day_key(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    d = dt.astimezone(timezone.utc).date()
    return d.isoformat()


def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


class DueAlertService:
    """Creates in-app notification rows for overdue and due-soon invoices; optional webhook."""

    def __init__(self, db: AsyncIOMotorDatabase[Any], settings: Settings) -> None:
        self._db = db
        self._inv = db[COLLECTION_INVOICES]
        self._notes = db[COLLECTION_NOTIFICATIONS]
        self._settings = settings

    async def run_due_checks(self) -> dict[str, int]:
        base: dict[str, Any] = {"$or": [{"status": "completed"}, {"status": {"$exists": False}}]}
        today = _today_start_utc()
        week_end = today + timedelta(days=self._settings.due_alert_days_ahead)

        ws_repo = WorkspaceRepository(self._db)
        workspaces = await ws_repo.list_all()
        workspace_ids = [d["_id"] for d in workspaces if d.get("_id")]

        created = 0
        webhook_payload: list[dict[str, Any]] = []
        day = _day_key(today)

        for wid in workspace_ids:
            if not isinstance(wid, ObjectId):
                continue

            overdue_cursor = self._inv.find(
                {
                    "$and": [
                        base,
                        {"workspace_id": wid},
                        {"due_date": {"$lt": today}},
                        {"due_date": {"$ne": None}},
                    ]
                },
                {"vendor_name": 1, "due_date": 1, "invoice_number": 1, "workspace_id": 1},
            )
            overdue_docs = await overdue_cursor.to_list(length=500)

            soon_cursor = self._inv.find(
                {
                    "$and": [
                        base,
                        {"workspace_id": wid},
                        {"due_date": {"$gte": today, "$lte": week_end}},
                    ]
                },
                {"vendor_name": 1, "due_date": 1, "invoice_number": 1, "workspace_id": 1},
            )
            soon_docs = await soon_cursor.to_list(length=500)

            for doc in overdue_docs:
                iid = str(doc["_id"])
                if await self._already_notified(iid, "overdue", day):
                    continue
                msg = self._msg_overdue(doc)
                await self._insert_note(wid, iid, "overdue", doc, msg, day)
                created += 1
                webhook_payload.append({"kind": "overdue", "invoice_id": iid, "message": msg})

            for doc in soon_docs:
                iid = str(doc["_id"])
                if await self._already_notified(iid, "due_soon", day):
                    continue
                msg = self._msg_due_soon(doc)
                await self._insert_note(wid, iid, "due_soon", doc, msg, day)
                created += 1
                webhook_payload.append({"kind": "due_soon", "invoice_id": iid, "message": msg})

        if webhook_payload and self._settings.alert_webhook_url.strip():
            await self._post_webhook(webhook_payload)

        logger.info("Due alert run: %s new notifications", created)
        return {"created": created}

    async def _already_notified(self, invoice_id: str, kind: str, day_key: str) -> bool:
        found = await self._notes.find_one(
            {"invoice_id": invoice_id, "kind": kind, "day_key": day_key},
        )
        return found is not None

    async def _insert_note(
        self,
        workspace_id: ObjectId,
        invoice_id: str,
        kind: str,
        inv_doc: dict[str, Any],
        message: str,
        day_key: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._notes.insert_one(
            {
                "workspace_id": workspace_id,
                "kind": kind,
                "invoice_id": invoice_id,
                "vendor_name": inv_doc.get("vendor_name"),
                "due_date": inv_doc.get("due_date"),
                "message": message,
                "created_at": now,
                "read": False,
                "day_key": day_key,
            }
        )

    def _msg_overdue(self, doc: dict[str, Any]) -> str:
        v = doc.get("vendor_name") or "Vendor"
        n = doc.get("invoice_number") or "unknown"
        return f"Overdue: {v} — invoice #{n}"

    def _msg_due_soon(self, doc: dict[str, Any]) -> str:
        v = doc.get("vendor_name") or "Vendor"
        n = doc.get("invoice_number") or "unknown"
        return f"Due soon: {v} — invoice #{n}"

    async def _post_webhook(self, payload: list[dict[str, Any]]) -> None:
        url = self._settings.alert_webhook_url.strip()
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                r = await client.post(url, json={"alerts": payload})
                r.raise_for_status()
        except Exception:
            logger.exception("Alert webhook POST failed")
