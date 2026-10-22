"""P3 / C6：AI 解析任务、候选审核与差异报告模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class ScriptParseRun(Base, TimestampMixin):
    """一次「开始解析本集」对应的一次 AI 解析运行。"""

    __tablename__ = "script_parse_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="解析运行 ID")
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("script_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="剧本文档 ID",
    )
    version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("script_document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="本次解析的剧本版本 ID",
    )
    worldbuilding_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("script_document_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="本次解析使用的世界观版本 ID",
    )
    task_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("generation_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="异步任务 ID",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        comment="pending / running / completed / failed / confirmed",
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="解析模型 ID")
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    prompt_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", comment="提示词版本标识"
    )
    prompt_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", comment="系统提示词 SHA-256"
    )
    input_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        index=True,
        comment="剧本 + 世界观 + 模型 + 提示词的输入哈希，用于幂等",
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failed_chunks: Mapped[list[int]] = mapped_column(
        JSON, nullable=False, default=list, comment="失败块序号"
    )
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="审核确认人",
    )
    applied_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None, comment="确认后实际创建/关联的统计"
    )
    confirmed_result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None, comment="确认后的结构化结果快照（P5 前不建正式场次）"
    )

    candidates: Mapped[list["ScriptParseCandidate"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ScriptParseCandidate.order_index",
    )


class ScriptParseCandidate(Base, TimestampMixin):
    """一条可独立审核的结构化候选。"""

    __tablename__ = "script_parse_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="候选 ID")
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("script_parse_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属解析运行 ID",
    )
    candidate_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="character / scene / prop / costume_change / scene_beat / dialogue / issue",
    )
    candidate_key: Mapped[str] = mapped_column(
        String(160), nullable=False, default="", comment="运行内稳定键"
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="结构化候选内容"
    )
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list, comment="原文证据"
    )
    review_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        comment="pending / edited / accepted / ignored / merged",
    )
    matched_entity_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="匹配到的已有业务实体 ID"
    )
    merged_into_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="合并目标候选 ID"
    )
    issue: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", comment="需要人工注意的问题"
    )

    run: Mapped["ScriptParseRun"] = relationship(back_populates="candidates")

    __table_args__ = (
        UniqueConstraint(
            "run_id", "candidate_type", "candidate_key", name="uq_script_parse_candidate_key"
        ),
        Index("ix_script_parse_candidates_run_type", "run_id", "candidate_type"),
    )


class ScriptDiffReport(Base, TimestampMixin):
    """同一文档两个版本之间的文本/结构化差异与影响范围。"""

    __tablename__ = "script_diff_reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="差异报告 ID")
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("script_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="剧本文档 ID",
    )
    old_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("script_document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    new_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("script_document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="draft",
        comment="draft / accepted / ignored",
    )
    text_diff: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list, comment="行级文本差异"
    )
    structured_diff: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="实体/对白/造型变化摘要"
    )
    impact: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="可能受影响的业务对象"
    )
    decisions: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="人工接受/忽略决策"
    )
    decided_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "old_version_id", "new_version_id", name="uq_script_diff_version_pair"
        ),
    )


__all__ = ["ScriptParseRun", "ScriptParseCandidate", "ScriptDiffReport"]
