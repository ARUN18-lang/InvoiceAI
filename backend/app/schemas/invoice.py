from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None
    # Optional GST breakdown (India); used for validation when present
    taxable_value: float | None = None
    gst_rate_pct: float | None = Field(default=None, description="Combined GST % e.g. 18 for 18%")
    cgst_amount: float | None = None
    sgst_amount: float | None = None
    igst_amount: float | None = None
    cess_amount: float | None = None


class ParsedInvoiceFields(BaseModel):
    """Structured fields produced by the LLM from raw document text."""

    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    vendor_name: str | None = None
    total_amount: float | None = None
    tax_amount: float | None = None
    currency: str | None = Field(default="INR")
    line_items: list[InvoiceLineItem] = Field(default_factory=list)
    expense_category: str | None = Field(
        default=None,
        description="One of: utilities, travel, office_supplies, software_subscriptions, vendor_payments, other",
    )
    category_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    detected_language: str | None = Field(default=None, description="ISO-ish label e.g. en, hi, kn")


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class InvoiceValidation(BaseModel):
    is_valid: bool = True
    issues: list[ValidationIssue] = Field(default_factory=list)
    fraud_flags: list[str] = Field(default_factory=list)


class InvoiceRecord(BaseModel):
    """API-facing view of a stored invoice (subset of Mongo document)."""

    id: str
    invoice_number: str | None
    invoice_date: date | None
    due_date: date | None
    vendor_name: str | None
    total_amount: float | None
    tax_amount: float | None
    currency: str | None
    line_items: list[InvoiceLineItem]
    category: str | None
    category_confidence: float | None
    validation: InvoiceValidation
    created_at: datetime
    mime_type: str | None = None
    status: Literal["processing", "completed", "failed"] = "completed"
    original_filename: str | None = None
    processing_error: str | None = None


class InvoiceCreateResult(BaseModel):
    invoice: InvoiceRecord
    extraction_backend: str | None = None
    raw_text_length: int | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=12_000)


class ChatSourceCitation(BaseModel):
    """One invoice snippet actually passed into the model context (not just an id)."""

    invoice_id: str
    vendor_name: str | None = None
    invoice_number: str | None = None
    total_amount: float | None = None
    category: str | None = None
    text_excerpt: str = Field(default="", description="Text chunk from this invoice used as context")
    via: Literal["semantic_search", "knowledge_graph"] = "semantic_search"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    invoice_ids: list[str] | None = None
    """Prior turns only (max 5 rounds = 10 messages). Current question is `message`."""
    history: list[ChatMessage] = Field(default_factory=list)

    def normalized_history(self) -> list[ChatMessage]:
        clean = [m for m in self.history if m.content and m.content.strip()]
        return clean[-10:]


class ChatResponse(BaseModel):
    answer: str
    source_invoice_ids: list[str] = Field(default_factory=list)
    source_citations: list[ChatSourceCitation] = Field(
        default_factory=list,
        description="Per-invoice text excerpts that were retrieved into context",
    )
    suggested_follow_ups: list[str] = Field(default_factory=list)
