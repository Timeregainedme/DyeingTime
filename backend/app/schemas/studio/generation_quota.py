"""P6 / C12：测试额度 schemas。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuotaStatusRead(BaseModel):
    scope: str
    media_type: str
    limit: int
    consumed: int
    reserved: int
    remaining: int


class QuotaReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope: str
    media_type: str
    amount: int
    status: str
    task_id: str | None = None
    provider: str = ""
    model: str = ""
    note: str = ""
    settled_at: datetime | None = None
    created_at: datetime | None = None


class QuotaReserveRequest(BaseModel):
    media_type: str = Field(..., pattern="^(image|video|audio)$")
    amount: int = Field(..., ge=1)
    task_id: str | None = None
    provider: str = ""
    model: str = ""
    note: str = ""


class QuotaSettleRequest(BaseModel):
    reservation_id: int
    commit: bool = True
