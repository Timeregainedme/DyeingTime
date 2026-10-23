"""P6 / C11：镜头参考绑定、@ 引用与不可变生成输入快照。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class ShotReferenceBinding(Base, TimestampMixin):
    """镜头级有序参考素材绑定。"""

    __tablename__ = "shot_reference_bindings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("files.id", ondelete="SET NULL"), nullable=True, index=True
    )
    asset_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="shot_reference", index=True,
        comment="character/scene/prop/costume/shot_reference",
    )
    asset_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    asset_version_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("asset_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reference_role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="shot_composition"
    )
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="auto", comment="auto/manual/uploaded"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("shot_id", "file_id", name="uq_shot_reference_bindings_shot_file"),
        Index("ix_shot_reference_bindings_order", "shot_id", "sort_order"),
    )


class ShotPromptReference(Base):
    """自然语言提示词中的 @ 资产引用，保存稳定对象 ID。"""

    __tablename__ = "shot_prompt_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_version_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("asset_versions.id", ondelete="SET NULL"), nullable=True
    )
    mention: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    start_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_shot_prompt_references_shot", "shot_id"),)


class ShotGenerationSnapshot(Base):
    """一次真实/模拟视频生成提交的不可变输入快照。"""

    __tablename__ = "shot_generation_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    shot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chapter_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scene_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("generation_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    reference_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="reference")
    manifest: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    natural_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    advanced_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    prompt_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    audio_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    asset_versions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    generation_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    style_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ratio: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    resolution: Mapped[str | None] = mapped_column(String(16), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    request_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True, comment="客户端幂等键；同一 key 只创建一个任务"
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_shot_generation_snapshots_shot_created", "shot_id", "created_at"),
        UniqueConstraint("shot_id", "request_key", name="uq_shot_generation_snapshots_request"),
    )


__all__ = ["ShotReferenceBinding", "ShotPromptReference", "ShotGenerationSnapshot"]
