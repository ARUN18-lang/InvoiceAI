from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class WorkspaceRecord(BaseModel):
    id: str
    name: str
    created_at: datetime
