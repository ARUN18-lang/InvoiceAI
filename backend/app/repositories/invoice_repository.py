from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.exceptions import NotFoundError
from app.schemas.invoice import InvoiceLineItem, InvoiceRecord, InvoiceValidation, ParsedInvoiceFields
from app.schemas.mongo_documents import COLLECTION_INVOICES


def _date_to_utc_datetime(d: date | datetime | None) -> datetime | None:
    if d is None:
        return None
    if isinstance(d, datetime):
        if d.tzinfo is None:
            return d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


class InvoiceRepository:
    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self._col = db[COLLECTION_INVOICES]

    async def insert(
        self,
        *,
        workspace_id: ObjectId,
        parsed: ParsedInvoiceFields,
        validation: InvoiceValidation,
        embedding: list[float],
        storage_path: str,
        original_filename: str,
        mime_type: str,
        extraction_backend: str,
        raw_text: str,
    ) -> str:
        vendor_normalized = " ".join((parsed.vendor_name or "").lower().split()) or None
        now = datetime.now(timezone.utc)
        preview = raw_text[:4000] if raw_text else None
        doc: dict[str, Any] = {
            "workspace_id": workspace_id,
            "invoice_number": parsed.invoice_number,
            "invoice_date": _date_to_utc_datetime(parsed.invoice_date),
            "due_date": _date_to_utc_datetime(parsed.due_date),
            "vendor_name": parsed.vendor_name,
            "vendor_normalized": vendor_normalized,
            "total_amount": parsed.total_amount,
            "tax_amount": parsed.tax_amount,
            "currency": parsed.currency or "INR",
            "line_items": [li.model_dump() for li in parsed.line_items],
            "category": parsed.expense_category,
            "category_confidence": parsed.category_confidence,
            "detected_language": parsed.detected_language,
            "validation": validation.model_dump(),
            "embedding": embedding or None,
            "raw_text": raw_text,
            "raw_text_preview": preview,
            "storage_path": storage_path,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "extraction_backend": extraction_backend,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def insert_processing_placeholder(
        self,
        *,
        workspace_id: ObjectId,
        storage_path: str,
        original_filename: str,
        mime_type: str,
    ) -> str:
        now = datetime.now(timezone.utc)
        doc: dict[str, Any] = {
            "workspace_id": workspace_id,
            "status": "processing",
            "processing_error": None,
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "vendor_name": None,
            "vendor_normalized": None,
            "total_amount": None,
            "tax_amount": None,
            "currency": "INR",
            "line_items": [],
            "category": None,
            "category_confidence": None,
            "detected_language": None,
            "validation": {"is_valid": True, "issues": [], "fraud_flags": []},
            "embedding": None,
            "raw_text": "",
            "raw_text_preview": None,
            "storage_path": storage_path,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "extraction_backend": None,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def complete_processing(
        self,
        invoice_id: str,
        workspace_id: ObjectId,
        *,
        parsed: ParsedInvoiceFields,
        validation: InvoiceValidation,
        embedding: list[float],
        extraction_backend: str,
        raw_text: str,
    ) -> None:
        try:
            oid = ObjectId(invoice_id)
        except Exception as e:
            raise NotFoundError("Invoice", invoice_id) from e
        vendor_normalized = " ".join((parsed.vendor_name or "").lower().split()) or None
        now = datetime.now(timezone.utc)
        preview = raw_text[:4000] if raw_text else None
        update: dict[str, Any] = {
            "status": "completed",
            "processing_error": None,
            "invoice_number": parsed.invoice_number,
            "invoice_date": _date_to_utc_datetime(parsed.invoice_date),
            "due_date": _date_to_utc_datetime(parsed.due_date),
            "vendor_name": parsed.vendor_name,
            "vendor_normalized": vendor_normalized,
            "total_amount": parsed.total_amount,
            "tax_amount": parsed.tax_amount,
            "currency": parsed.currency or "INR",
            "line_items": [li.model_dump() for li in parsed.line_items],
            "category": parsed.expense_category,
            "category_confidence": parsed.category_confidence,
            "detected_language": parsed.detected_language,
            "validation": validation.model_dump(),
            "embedding": embedding or None,
            "raw_text": raw_text,
            "raw_text_preview": preview,
            "extraction_backend": extraction_backend,
            "updated_at": now,
        }
        res = await self._col.update_one({"_id": oid, "workspace_id": workspace_id}, {"$set": update})
        if res.matched_count == 0:
            raise NotFoundError("Invoice", invoice_id)

    async def mark_failed(self, invoice_id: str, workspace_id: ObjectId, error_message: str) -> None:
        try:
            oid = ObjectId(invoice_id)
        except Exception:
            return
        now = datetime.now(timezone.utc)
        await self._col.update_one(
            {"_id": oid, "workspace_id": workspace_id},
            {
                "$set": {
                    "status": "failed",
                    "processing_error": error_message[:2000],
                    "updated_at": now,
                }
            },
        )

    async def list_recent(self, workspace_id: ObjectId, limit: int = 50) -> list[InvoiceRecord]:
        cap = min(max(limit, 1), 200)
        cursor = self._col.find({"workspace_id": workspace_id}).sort("created_at", -1).limit(cap)
        docs = await cursor.to_list(length=cap)
        return [self._to_record(d) for d in docs]

    async def get(self, invoice_id: str, workspace_id: ObjectId) -> InvoiceRecord:
        try:
            oid = ObjectId(invoice_id)
        except Exception as e:
            raise NotFoundError("Invoice", invoice_id) from e
        doc = await self._col.find_one({"_id": oid, "workspace_id": workspace_id})
        if not doc:
            raise NotFoundError("Invoice", invoice_id)
        return self._to_record(doc)

    async def get_extraction_meta(
        self, invoice_id: str, workspace_id: ObjectId
    ) -> tuple[str | None, int | None]:
        try:
            oid = ObjectId(invoice_id)
        except Exception:
            return None, None
        doc = await self._col.find_one(
            {"_id": oid, "workspace_id": workspace_id},
            {"extraction_backend": 1, "raw_text": 1},
        )
        if not doc:
            return None, None
        raw = doc.get("raw_text") or ""
        return doc.get("extraction_backend"), (len(raw) if raw else None)

    def _to_record(self, doc: dict[str, Any]) -> InvoiceRecord:
        items_raw = doc.get("line_items") or []
        line_items = [InvoiceLineItem.model_validate(x) for x in items_raw]
        val_raw = doc.get("validation") or {}
        validation = InvoiceValidation.model_validate(val_raw)
        inv_date = doc.get("invoice_date")
        due = doc.get("due_date")

        def _as_date(value: Any) -> date | None:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            return None

        created = doc.get("created_at") or datetime.now(timezone.utc)

        raw_status = doc.get("status") or "completed"
        if raw_status not in ("processing", "completed", "failed"):
            raw_status = "completed"

        return InvoiceRecord(
            id=str(doc["_id"]),
            invoice_number=doc.get("invoice_number"),
            invoice_date=_as_date(inv_date),
            due_date=_as_date(due),
            vendor_name=doc.get("vendor_name"),
            total_amount=doc.get("total_amount"),
            tax_amount=doc.get("tax_amount"),
            currency=doc.get("currency"),
            line_items=line_items,
            category=doc.get("category"),
            category_confidence=doc.get("category_confidence"),
            validation=validation,
            created_at=created if isinstance(created, datetime) else datetime.now(timezone.utc),
            mime_type=doc.get("mime_type"),
            status=raw_status,
            original_filename=doc.get("original_filename"),
            processing_error=doc.get("processing_error"),
        )
