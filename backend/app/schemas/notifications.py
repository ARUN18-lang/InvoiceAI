from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class NotificationRecord(BaseModel):
    id: str
    kind: Literal["due_soon", "overdue"]
    invoice_id: str
    vendor_name: str | None = None
    due_date: date | None = None
    message: str
    created_at: datetime
    read: bool = False
