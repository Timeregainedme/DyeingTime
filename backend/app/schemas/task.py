from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.task_manager.types import DeliveryMode, TaskStatus


class TaskCreate(BaseModel):
    mode: DeliveryMode = Field(..., description="交付方式")
    payload: dict[str, Any] = Field(default_factory=dict, description="任务参数（JSON）")


class TaskStatusRead(BaseModel):
    id: str
    status: TaskStatus
    progress: int = Field(..., ge=0, le=100, description="进度 0-100")
    result: dict[str, Any] | None = None
    error: str = ""
    started_at_ts: float | None = None
    finished_at_ts: float | None = None
    elapsed_ms: int | None = None
    updated_at_ts: float | None = None


class TaskCreateRead(BaseModel):
    id: str
    mode: DeliveryMode
    status: TaskStatus
    progress: int = Field(..., ge=0, le=100)
