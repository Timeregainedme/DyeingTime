"""P6 / C13：视频批量生成批次与子任务。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class VideoGenerationBatch(Base, TimestampMixin):
    __tablename__ = "video_generation_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scene_group_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("scene_groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    requested_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="queued", index=True,
        comment="queued/running/succeeded/failed/cancelled/partial_success",
    )
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    queued_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    running_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancelled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    coordinator_task_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("generation_tasks.id", ondelete="SET NULL"), nullable=True
    )

    items: Mapped[list["VideoGenerationBatchItem"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="VideoGenerationBatchItem.id",
    )


class VideoGenerationBatchItem(Base, TimestampMixin):
    __tablename__ = "video_generation_batch_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("video_generation_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    task_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("generation_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="queued", index=True,
        comment="queued/running/succeeded/failed/cancelled",
    )
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enqueued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    batch: Mapped["VideoGenerationBatch"] = relationship(back_populates="items")

    __table_args__ = (
        UniqueConstraint("batch_id", "shot_id", "candidate_index", name="uq_video_batch_shot_candidate"),
        Index("ix_video_batch_items_batch_status", "batch_id", "status"),
    )


__all__ = ["VideoGenerationBatch", "VideoGenerationBatchItem"]
