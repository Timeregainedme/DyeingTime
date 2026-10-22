"""P4：角色别名、资产版本与图片候选模型。

设计边界：
- `Character` / `Scene` / `Prop` / `Costume` 仍是唯一业务主实体；
- 版本与候选图通过多态 `asset_type + asset_id` 关联，不复制主实体；
- 版本行是历史快照，已采纳版本不原地修改；
- 图片候选与已采纳图片分开，重新抽卡不会自动替换当前形象。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
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


class CharacterAlias(Base, TimestampMixin):
    """角色别名/称谓。"""

    __tablename__ = "character_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="角色 ID",
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始别名/称谓")
    normalized_alias: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="归一化别名（去空白/小写）"
    )
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="manual", comment="来源：manual / p3_parse"
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    character: Mapped["Character"] = relationship(back_populates="aliases")

    __table_args__ = (
        UniqueConstraint(
            "character_id", "normalized_alias", name="uq_character_aliases_character_alias"
        ),
    )


class AssetVersion(Base, TimestampMixin):
    """角色身份/造型，或场景/道具/服装的基础/衍生版本。"""

    __tablename__ = "asset_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="版本 ID")
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="项目 ID",
    )
    asset_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="character / scene / prop / costume",
    )
    asset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="主实体 ID")
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="资产内版本号")
    parent_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("asset_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="父版本 ID（衍生版本来源）",
    )
    version_kind: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="base",
        comment="identity / appearance / base / derived",
    )
    variant_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="base",
        comment="base / costume / hairstyle / makeup / age / weather / lighting / other",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="", comment="版本名称")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="版本描述")
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="结构化属性（服装 ID、发型、妆容等）"
    )
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="manual",
        comment="来源：manual / generated / uploaded / p3_confirm",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="draft",
        comment="draft / active / superseded",
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    candidates: Mapped[list["AssetImageCandidate"]] = relationship(
        back_populates="version",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "asset_type", "asset_id", "version_no", name="uq_asset_versions_asset_no"
        ),
        Index("ix_asset_versions_scope", "project_id", "asset_type", "asset_id"),
    )


class AssetImageCandidate(Base, TimestampMixin):
    """一次生成或上传得到的资产图片候选。"""

    __tablename__ = "asset_image_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="项目 ID",
    )
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    asset_version_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("asset_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属资产版本；采纳后回填/创建",
    )
    candidate_batch_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", index=True, comment="候选批次 ID"
    )
    view_angle: Mapped[str] = mapped_column(
        String(32), nullable=False, default="FRONT", index=True, comment="FRONT/LEFT/RIGHT/BACK/THREE_QUARTER"
    )
    quality_level: Mapped[str] = mapped_column(
        String(16), nullable=False, default="low", comment="low/medium/high"
    )
    file_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="图片文件 ID",
    )
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="generated", comment="generated / uploaded"
    )
    generation_task_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("generation_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="生成任务 ID",
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="生成提示词")
    generation_params: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="模型/比例/分辨率等生成参数"
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        comment="pending / succeeded / failed / adopted / discarded",
    )
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str] = mapped_column(String(32), nullable=False, default="png")
    is_adopted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否已被用户采纳"
    )
    adopted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    adopted_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    version: Mapped["AssetVersion | None"] = relationship(back_populates="candidates")

    __table_args__ = (
        Index("ix_asset_image_candidates_scope", "project_id", "asset_type", "asset_id"),
        Index("ix_asset_image_candidates_batch", "candidate_batch_id"),
    )


__all__ = ["CharacterAlias", "AssetVersion", "AssetImageCandidate"]
