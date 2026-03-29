from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.analytics import AnalyticsDashboard, CategorySpend, MonthlySpend, VendorTop
from app.schemas.mongo_documents import COLLECTION_INVOICES


def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


def _completed_match() -> dict[str, Any]:
    return {"$or": [{"status": "completed"}, {"status": {"$exists": False}}]}


def _workspace_base(workspace_id: ObjectId) -> dict[str, Any]:
    return {"$and": [_completed_match(), {"workspace_id": workspace_id}]}


class AnalyticsService:
    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self._inv = db[COLLECTION_INVOICES]

    async def dashboard(self, *, workspace_id: ObjectId, top_vendors: int = 8) -> AnalyticsDashboard:
        base = _workspace_base(workspace_id)
        today = _today_start_utc()
        week_end = today + timedelta(days=7)

        total_cur = self._inv.aggregate(
            [
                {"$match": base},
                {
                    "$group": {
                        "_id": None,
                        "invoice_count": {"$sum": 1},
                        "total_spend": {"$sum": {"$ifNull": ["$total_amount", 0]}},
                        "total_tax": {"$sum": {"$ifNull": ["$tax_amount", 0]}},
                    }
                },
            ]
        )
        totals = await total_cur.to_list(length=1)
        t0 = totals[0] if totals else {}
        invoice_count = int(t0.get("invoice_count") or 0)
        total_spend = float(t0.get("total_spend") or 0.0)
        total_tax = float(t0.get("total_tax") or 0.0)

        overdue_count = await self._inv.count_documents(
            {"$and": [base, {"due_date": {"$lt": today}}, {"due_date": {"$ne": None}}]}
        )
        due_soon_count = await self._inv.count_documents(
            {
                "$and": [
                    base,
                    {"due_date": {"$gte": today, "$lte": week_end}},
                ]
            }
        )

        cat_cur = self._inv.aggregate(
            [
                {"$match": base},
                {
                    "$group": {
                        "_id": {"$ifNull": ["$category", "other"]},
                        "total_amount": {"$sum": {"$ifNull": ["$total_amount", 0]}},
                        "invoice_count": {"$sum": 1},
                    }
                },
                {"$sort": {"total_amount": -1}},
            ]
        )
        cat_rows = await cat_cur.to_list(length=50)
        by_category = [
            CategorySpend(
                category=str(r["_id"]),
                total_amount=float(r.get("total_amount") or 0),
                invoice_count=int(r.get("invoice_count") or 0),
            )
            for r in cat_rows
        ]

        ven_cur = self._inv.aggregate(
            [
                {"$match": {**base, "vendor_name": {"$nin": [None, ""]}}},
                {
                    "$group": {
                        "_id": "$vendor_name",
                        "total_amount": {"$sum": {"$ifNull": ["$total_amount", 0]}},
                        "invoice_count": {"$sum": 1},
                    }
                },
                {"$sort": {"total_amount": -1}},
                {"$limit": top_vendors},
            ]
        )
        ven_rows = await ven_cur.to_list(length=top_vendors)
        top_vendors_list = [
            VendorTop(
                vendor_name=str(r["_id"]),
                total_amount=float(r.get("total_amount") or 0),
                invoice_count=int(r.get("invoice_count") or 0),
            )
            for r in ven_rows
        ]

        month_cur = self._inv.aggregate(
            [
                {"$match": {**base, "invoice_date": {"$ne": None}}},
                {
                    "$group": {
                        "_id": {
                            "y": {"$year": "$invoice_date"},
                            "m": {"$month": "$invoice_date"},
                        },
                        "total_amount": {"$sum": {"$ifNull": ["$total_amount", 0]}},
                        "invoice_count": {"$sum": 1},
                    }
                },
                {"$sort": {"_id.y": -1, "_id.m": -1}},
                {"$limit": 18},
            ]
        )
        month_rows = await month_cur.to_list(length=18)
        monthly: list[MonthlySpend] = []
        for r in month_rows:
            ident = r["_id"]
            y, m = int(ident["y"]), int(ident["m"])
            monthly.append(
                MonthlySpend(
                    month=f"{y:04d}-{m:02d}",
                    total_amount=float(r.get("total_amount") or 0),
                    invoice_count=int(r.get("invoice_count") or 0),
                )
            )
        monthly.sort(key=lambda x: x.month)

        return AnalyticsDashboard(
            invoice_count=invoice_count,
            total_spend=total_spend,
            total_tax=total_tax,
            overdue_count=int(overdue_count),
            due_within_7d_count=int(due_soon_count),
            by_category=by_category,
            top_vendors=top_vendors_list,
            monthly=monthly,
        )
