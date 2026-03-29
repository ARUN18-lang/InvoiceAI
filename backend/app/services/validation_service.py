from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.invoice import InvoiceValidation, ParsedInvoiceFields, ValidationIssue
from app.schemas.mongo_documents import COLLECTION_INVOICES


def _normalize_vendor(name: str | None) -> str | None:
    if not name:
        return None
    return " ".join(name.lower().split())


def _gst_line_issues(parsed: ParsedInvoiceFields) -> list[ValidationIssue]:
    lines = parsed.line_items or []
    if not lines:
        return []
    issues: list[ValidationIssue] = []
    eps = 1.0
    rel = 0.02

    sum_lines = sum((li.amount or 0.0) for li in lines)
    if parsed.total_amount is not None and sum_lines > 0:
        diff = abs(sum_lines - float(parsed.total_amount))
        if diff > max(eps, abs(parsed.total_amount) * rel):
            issues.append(
                ValidationIssue(
                    code="line_total_mismatch",
                    message=(
                        f"Sum of line amounts ({sum_lines:.2f}) differs from invoice total "
                        f"({parsed.total_amount:.2f})"
                    ),
                    severity="warning",
                )
            )

    for i, li in enumerate(lines):
        tag = f"Line {i + 1}"
        has_gst = any(
            x is not None
            for x in (
                li.cgst_amount,
                li.sgst_amount,
                li.igst_amount,
                li.cess_amount,
                li.taxable_value,
                li.gst_rate_pct,
            )
        )
        if not has_gst:
            continue

        cgst = float(li.cgst_amount or 0.0)
        sgst = float(li.sgst_amount or 0.0)
        igst = float(li.igst_amount or 0.0)
        cess = float(li.cess_amount or 0.0)

        if igst > 0 and (cgst > 0 or sgst > 0):
            issues.append(
                ValidationIssue(
                    code="gst_mixed_igst_cgst_sgst",
                    message=f"{tag}: both IGST and CGST/SGST present — verify inter vs intra-state",
                    severity="warning",
                )
            )

        if cgst > 0 and sgst > 0:
            mx = max(cgst, sgst, 1.0)
            if abs(cgst - sgst) > max(0.5, 0.05 * mx):
                issues.append(
                    ValidationIssue(
                        code="gst_cgst_sgst_asymmetry",
                        message=f"{tag}: CGST and SGST usually match for intra-state supplies",
                        severity="info",
                    )
                )

        if li.taxable_value is not None:
            expected_tax = cgst + sgst + igst + cess
            derived = float(li.taxable_value) + expected_tax
            if li.amount is not None and abs(derived - float(li.amount)) > max(
                eps, abs(li.amount) * rel
            ):
                issues.append(
                    ValidationIssue(
                        code="gst_line_taxable_mismatch",
                        message=(
                            f"{tag}: taxable ({li.taxable_value}) + taxes ({expected_tax:.2f}) "
                            f"does not match line amount ({li.amount})"
                        ),
                        severity="warning",
                    )
                )

        if li.gst_rate_pct is not None and li.taxable_value is not None and li.taxable_value > 0:
            rate = float(li.gst_rate_pct) / 100.0
            expected_gst = float(li.taxable_value) * rate
            actual_gst = cgst + sgst + igst
            if actual_gst > 0 and abs(actual_gst - expected_gst) > max(eps, expected_gst * rel):
                issues.append(
                    ValidationIssue(
                        code="gst_rate_vs_components",
                        message=(
                            f"{tag}: tax components ({actual_gst:.2f}) vs taxable×rate "
                            f"({expected_gst:.2f} @ {li.gst_rate_pct}%)"
                        ),
                        severity="info",
                    )
                )

    return issues


class InvoiceValidationService:
    """
    Rule-based validation and simple fraud heuristics after LLM extraction.

    Duplicate checks query Mongo for prior invoices with same number + vendor.
    """

    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self._db = db

    async def validate(
        self,
        parsed: ParsedInvoiceFields,
        *,
        exclude_id: Any | None = None,
        workspace_id: ObjectId | None = None,
    ) -> InvoiceValidation:
        issues: list[ValidationIssue] = []
        fraud_flags: list[str] = []

        today = datetime.now(timezone.utc).date()

        if not parsed.invoice_number:
            issues.append(
                ValidationIssue(code="missing_invoice_number", message="Invoice number is missing", severity="error")
            )
        if not parsed.vendor_name:
            issues.append(
                ValidationIssue(code="missing_vendor", message="Vendor name is missing", severity="warning")
            )
        if parsed.total_amount is None:
            issues.append(
                ValidationIssue(code="missing_total", message="Total amount is missing", severity="error")
            )

        if parsed.invoice_date:
            if parsed.invoice_date > today:
                issues.append(
                    ValidationIssue(
                        code="future_invoice_date",
                        message="Invoice date is in the future",
                        severity="warning",
                    )
                )
                fraud_flags.append("future_invoice_date")

        if parsed.due_date and parsed.invoice_date and parsed.due_date < parsed.invoice_date:
            issues.append(
                ValidationIssue(
                    code="due_before_invoice",
                    message="Due date is before invoice date",
                    severity="warning",
                )
            )

        if parsed.total_amount is not None and parsed.tax_amount is not None and parsed.tax_amount < 0:
            issues.append(
                ValidationIssue(code="negative_tax", message="Tax amount is negative", severity="warning")
            )

        if (
            parsed.total_amount is not None
            and parsed.tax_amount is not None
            and parsed.tax_amount > parsed.total_amount
        ):
            issues.append(
                ValidationIssue(
                    code="tax_exceeds_total",
                    message="Tax amount exceeds total — possible extraction error",
                    severity="warning",
                )
            )
            fraud_flags.append("gst_tax_mismatch")

        if parsed.total_amount is not None and parsed.total_amount > 1_000_000:
            fraud_flags.append("unusually_high_amount")

        vendor_key = _normalize_vendor(parsed.vendor_name)
        if parsed.invoice_number and vendor_key:
            dup_query: dict[str, Any] = {
                "invoice_number": parsed.invoice_number,
                "vendor_normalized": vendor_key,
            }
            if workspace_id is not None:
                dup_query["workspace_id"] = workspace_id
            if exclude_id is not None:
                dup_query["_id"] = {"$ne": exclude_id}
            existing = await self._db[COLLECTION_INVOICES].find_one(dup_query)
            if existing:
                fraud_flags.append("duplicate_invoice_number")
                issues.append(
                    ValidationIssue(
                        code="duplicate_invoice",
                        message="Another invoice exists with the same number and vendor",
                        severity="warning",
                    )
                )

        if vendor_key and parsed.total_amount is not None:
            repeat_filter: dict[str, Any] = {
                "vendor_normalized": vendor_key,
                "total_amount": parsed.total_amount,
            }
            if workspace_id is not None:
                repeat_filter["workspace_id"] = workspace_id
            if exclude_id is not None:
                repeat_filter["_id"] = {"$ne": exclude_id}
            repeat = await self._db[COLLECTION_INVOICES].count_documents(repeat_filter)
            if repeat >= 1:
                fraud_flags.append("same_vendor_same_amount_pattern")
                issues.append(
                    ValidationIssue(
                        code="repeated_amount_vendor",
                        message="Multiple invoices from this vendor with identical totals",
                        severity="info",
                    )
                )

        issues.extend(_gst_line_issues(parsed))

        is_valid = not any(i.severity == "error" for i in issues)
        return InvoiceValidation(is_valid=is_valid, issues=issues, fraud_flags=fraud_flags)
