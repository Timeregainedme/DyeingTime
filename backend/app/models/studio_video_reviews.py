"""P6 / C14：视频候选人工审核记录。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class ShotVideoReview(Base, TimestampMixin):
    __tablename__ = "shot_video_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("generation_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("files.id", ondelete="SET NULL"), nullable=True, index=True
    )
    review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unrated",
        comment="unrated/satisfied/unsatisfied",
    )
    issue_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("task_id", name="uq_shot_video_reviews_task"),
        Index("ix_shot_video_reviews_shot_status", "shot_id", "review_status"),
    )


__all__ = ["ShotVideoReview"]
