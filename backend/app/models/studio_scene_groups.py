"""P5：正式场次（SceneGroup）。

SceneGroup 是剧集内的剧情分组；Scene 是可复用场景资产。二者不合并。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class SceneGroup(Base, TimestampMixin):
    """剧集内的一段连续剧情场次。"""

    __tablename__ = "scene_groups"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="场次 ID")
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID（便于项目级查询）",
    )
    chapter_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属剧集 ID",
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False, comment="剧集内场次顺序")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="", comment="场次标题")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="场次描述")
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="", comment="地点文字")
    time_of_day: Mapped[str] = mapped_column(String(64), nullable=False, default="", comment="时间")
    story_event: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="关键剧情事件")
    primary_scene_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="主场景资产 ID；与场次本身区分",
    )
    source_parse_run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("script_parse_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="来源 P3 解析运行 ID",
    )
    source_beat_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="来源 scene_beat 稳定键"
    )
    source_start_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_end_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    shots: Mapped[list["Shot"]] = relationship(
        back_populates="scene_group",
        passive_deletes=True,
        order_by="Shot.index",
    )

    __table_args__ = (
        UniqueConstraint("chapter_id", "index", name="uq_scene_groups_chapter_index"),
        UniqueConstraint(
            "chapter_id",
            "source_parse_run_id",
            "source_beat_key",
            name="uq_scene_groups_source_beat",
        ),
        Index("ix_scene_groups_project_chapter", "project_id", "chapter_id"),
    )


__all__ = ["SceneGroup"]
