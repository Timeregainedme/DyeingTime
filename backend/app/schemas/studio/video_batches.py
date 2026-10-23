"""P6 / C13：视频批量任务 schemas。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VideoBatchCreate(BaseModel):
    shot_ids: list[str] = Field(..., min_length=1, max_length=100)
    candidate_count: int = Field(1, ge=1, le=2)
    concurrency: int | None = Field(None, ge=1, le=8)
    scene_group_id: str | None = None
    allow_low_coverage: bool = Field(False, description="分镜覆盖率低时需显式确认")


class VideoBatchItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: str
    shot_id: str
    candidate_index: int
    task_id: str | None = None
    status: str
    error: str = ""
    enqueued_at: datetime | None = None
    completed_at: datetime | None = None


class VideoBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    chapter_id: str
    scene_group_id: str | None = None
    status: str
    candidate_count: int
    concurrency: int
    total_count: int
    queued_count: int
    running_count: int
    succeeded_count: int
    failed_count: int
    cancelled_count: int
    coverage_snapshot: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    coordinator_task_id: str | None = None
    created_at: datetime | None = None
    items: list[VideoBatchItemRead] = Field(default_factory=list)


class VideoBatchListRead(BaseModel):
    items: list[VideoBatchRead] = Field(default_factory=list)


class VideoBatchRetryRequest(BaseModel):
    item_ids: list[int] | None = None
