"""P5：分镜规划草稿、候选镜头与镜头资产版本选择。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class ShotPlanDraft(Base, TimestampMixin):
    """一次 AI 分镜规划的草稿与任务信息。"""

    __tablename__ = "shot_plan_drafts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_parse_run_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("script_parse_runs.id", ondelete="SET NULL"), nullable=True
    )
    source_script_version_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("script_document_versions.id", ondelete="SET NULL"), nullable=True
    )
    target_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    pace: Mapped[str] = mapped_column(String(16), nullable=False, default="standard")
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="draft", index=True,
        comment="draft/generating/review_required/confirmed/failed",
    )
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    task_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("generation_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    scene_group_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list, comment="规划时场次结构快照"
    )
    coverage: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="剧情覆盖统计与问题"
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    candidates: Mapped[list["ShotPlanCandidate"]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ShotPlanCandidate.order_index",
    )

    __table_args__ = (
        Index("ix_shot_plan_drafts_chapter_status", "chapter_id", "status"),
    )


class ShotPlanCandidate(Base, TimestampMixin):
    """可独立审核/编辑的镜头规划候选。"""

    __tablename__ = "shot_plan_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    draft_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shot_plan_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    scene_group_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("scene_groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    candidate_key: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", comment="pending/edited/accepted/ignored"
    )
    source_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    draft: Mapped["ShotPlanDraft"] = relationship(back_populates="candidates")

    __table_args__ = (
        UniqueConstraint("draft_id", "candidate_key", name="uq_shot_plan_candidates_key"),
        Index("ix_shot_plan_candidates_draft_order", "draft_id", "order_index"),
    )


class ShotAssetVersion(Base):
    """镜头级资产版本选择（P5），不包含 P6 的参考图片绑定。"""

    __tablename__ = "shot_asset_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True, comment="character/scene/prop/costume"
    )
    asset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    asset_version_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("asset_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="base",
        comment="character_identity/character_appearance/scene/prop/costume",
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="plan")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "shot_id", "asset_type", "asset_id", "role",
            name="uq_shot_asset_versions_shot_asset_role",
        ),
        Index("ix_shot_asset_versions_shot_type", "shot_id", "asset_type"),
    )


class ShotPlanAppliedShot(Base):
    """规划候选到正式镜头的映射，保证重复确认幂等。"""

    __tablename__ = "shot_plan_applied_shots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shot_plan_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("shot_plan_candidates.id", ondelete="SET NULL"), nullable=True
    )
    shot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("draft_id", "candidate_id", name="uq_shot_plan_applied_candidate"),
        UniqueConstraint("draft_id", "shot_id", name="uq_shot_plan_applied_shot"),
    )


__all__ = [
    "ShotPlanDraft",
    "ShotPlanCandidate",
    "ShotAssetVersion",
    "ShotPlanAppliedShot",
]
