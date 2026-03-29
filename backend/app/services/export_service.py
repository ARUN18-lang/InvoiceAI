from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.mongo_documents import COLLECTION_INVOICES


def _completed_match() -> dict[str, Any]:
    return {"$or": [{"status": "completed"}, {"status": {"$exists": False}}]}


def _workspace_scope(workspace_id: ObjectId) -> dict[str, Any]:
    return {"$and": [_completed_match(), {"workspace_id": workspace_id}]}


def _iso(d: date | datetime | None) -> str | None:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date().isoformat()
    return d.isoformat()


class ExportService:
    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self._inv = db[COLLECTION_INVOICES]

    async def fetch_rows(self, workspace_id: ObjectId, limit: int = 2000) -> list[dict[str, Any]]:
        cap = min(max(limit, 1), 5000)
        cursor = self._inv.find(
            _workspace_scope(workspace_id),
            {
                "vendor_name": 1,
                "invoice_number": 1,
                "invoice_date": 1,
                "due_date": 1,
                "total_amount": 1,
                "tax_amount": 1,
                "currency": 1,
                "category": 1,
                "line_items": 1,
                "created_at": 1,
            },
        ).sort("created_at", -1).limit(cap)
        docs = await cursor.to_list(length=cap)
        rows: list[dict[str, Any]] = []
        for d in docs:
            rows.append(
                {
                    "id": str(d["_id"]),
                    "vendor_name": d.get("vendor_name"),
                    "invoice_number": d.get("invoice_number"),
                    "invoice_date": _iso(d.get("invoice_date")),
                    "due_date": _iso(d.get("due_date")),
                    "total_amount": d.get("total_amount"),
                    "tax_amount": d.get("tax_amount"),
                    "currency": d.get("currency"),
                    "category": d.get("category"),
                    "line_item_count": len(d.get("line_items") or []),
                    "created_at": d.get("created_at").isoformat() if d.get("created_at") else None,
                }
            )
        return rows

    async def as_json_bytes(self, workspace_id: ObjectId, limit: int) -> bytes:
        rows = await self.fetch_rows(workspace_id, limit)
        return json.dumps(rows, indent=2).encode("utf-8")

    async def as_csv_bytes(self, workspace_id: ObjectId, limit: int) -> bytes:
        rows = await self.fetch_rows(workspace_id, limit)
        buf = io.StringIO()
        if not rows:
            writer = csv.writer(buf)
            writer.writerow(
                [
                    "id",
                    "vendor_name",
                    "invoice_number",
                    "invoice_date",
                    "due_date",
                    "total_amount",
                    "tax_amount",
                    "currency",
                    "category",
                    "line_item_count",
                    "created_at",
                ]
            )
            return buf.getvalue().encode("utf-8")
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
        return buf.getvalue().encode("utf-8")

    async def as_xlsx_bytes(self, workspace_id: ObjectId, limit: int) -> bytes:
        from openpyxl import Workbook

        rows = await self.fetch_rows(workspace_id, limit)
        wb = Workbook()
        ws = wb.active
        ws.title = "Invoices"
        headers = [
            "id",
            "vendor_name",
            "invoice_number",
            "invoice_date",
            "due_date",
            "total_amount",
            "tax_amount",
            "currency",
            "category",
            "line_item_count",
            "created_at",
        ]
        ws.append(headers)
        for r in rows:
            ws.append([r.get(h) for h in headers])
        bio = io.BytesIO()
        wb.save(bio)
        return bio.getvalue()
