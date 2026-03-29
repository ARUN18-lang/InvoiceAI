from __future__ import annotations

from pydantic import BaseModel, Field


class CategorySpend(BaseModel):
    category: str
    total_amount: float = 0.0
    invoice_count: int = 0


class VendorTop(BaseModel):
    vendor_name: str
    total_amount: float = 0.0
    invoice_count: int = 0


class MonthlySpend(BaseModel):
    month: str = Field(description="YYYY-MM")
    total_amount: float = 0.0
    invoice_count: int = 0


class AnalyticsDashboard(BaseModel):
    invoice_count: int = 0
    total_spend: float = 0.0
    total_tax: float = 0.0
    overdue_count: int = 0
    due_within_7d_count: int = 0
    by_category: list[CategorySpend] = Field(default_factory=list)
    top_vendors: list[VendorTop] = Field(default_factory=list)
    monthly: list[MonthlySpend] = Field(default_factory=list)
