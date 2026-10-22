from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin
from app.models.types import ChapterStatus, ProjectVisualStyle

if TYPE_CHECKING:
    from app.models.studio_assets import Actor, Character, Costume, Prop, Scene
    from app.models.studio_shots import Shot
    from app.models.workspace import Workspace


class Project(Base, TimestampMixin):
    """项目表。

    说明：
    - `stats` 使用 JSON 存储聚合统计，便于快速渲染与渐进扩展；如需要强一致统计可后续改为物化/触发器维护。
    """

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="项目 ID")
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名称")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="项目简介")
    style: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="题材/风格（风格目录名称；兼容历史枚举值）",
    )
    visual_style: Mapped[ProjectVisualStyle] = mapped_column(
        String(16),
        nullable=False,
        default=ProjectVisualStyle.live_action,
        comment="画面表现形式（真人/动漫等）",
    )
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="随机种子")
    unify_style: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否统一风格（跨章节）")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="进度百分比（0-100）")
    default_video_ratio: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        default=None,
        comment="项目级默认视频比例（可为空；分镜未覆盖时使用）",
    )
    default_image_ratio: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        default=None,
        comment="项目级默认图片比例（可为空；为空时回落到 default_video_ratio）",
    )
    use_dialog_audio_as_reference: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="视频生成时是否自动带上镜头台词已生成的配音作为参考音频（新项目默认关闭）",
    )
    default_image_resolution_profile: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        default=None,
        comment="项目级默认图片分辨率档位（standard/high；为空时回落到提供方默认档位）",
    )
    default_video_resolution: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        default=None,
        comment="项目级默认视频分辨率档位（如 768p/2k；为空时回落到提供方默认档位）",
    )

    # --- P2：项目级生成配置与模型快照 ---
    # 只存模型 ID；API Key / Base URL 等凭据始终由服务端按 provider_id 解析。
    default_image_model_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="项目默认图片模型 ID；为空回退全局默认",
    )
    default_video_model_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="项目默认视频模型 ID；为空回退全局默认",
    )
    default_audio_model_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="项目默认音频模型 ID；为空回退全局默认",
    )
    default_reference_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="reference",
        comment="H3 默认参考模式（reference=多参考）",
    )
    default_shot_duration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        comment="项目默认镜头时长（秒）",
    )
    video_duration_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=4,
        comment="项目业务时长下限（秒）",
    )
    video_duration_max: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=15,
        comment="项目业务时长上限（秒）",
    )
    video_concurrency: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=4,
        comment="视频批量并发数（默认 4）",
    )
    generation_config_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="生成配置版本；确认时递增",
    )
    generation_config_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="生成配置确认时间；为空表示未确认",
    )
    generation_config_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="生成配置最近保存时间",
    )
    generation_config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="已确认的生成配置快照（不含凭据）",
    )

    stats: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict, comment="聚合统计（JSON）")

    # --- 多租户归属（Phase 1）---
    # 放在 projects 而不是给 54 张表都加列：章节/镜头/资产均通过项目间接归属，
    # 鉴权时只需校验一次项目归属即可覆盖其下全部资源。
    workspace_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="所属工作区（多租户边界）",
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="创建者账号（账号删除后置空，项目保留）",
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="projects")

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    characters: Mapped[list["Character"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Character.id",
    )
    actor_links: Mapped[list["ProjectActorLink"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProjectActorLink.id",
    )
    scene_links: Mapped[list["ProjectSceneLink"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProjectSceneLink.id",
    )
    prop_links: Mapped[list["ProjectPropLink"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProjectPropLink.id",
    )
    costume_links: Mapped[list["ProjectCostumeLink"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProjectCostumeLink.id",
    )

    __table_args__ = (
        Index("ix_projects_updated_at", "updated_at"),
        Index("ix_projects_style", "style"),
        Index("ix_projects_visual_style", "visual_style"),
    )


class Chapter(Base, TimestampMixin):
    """章节表。

    约束：
    - `project_id + index` 唯一，保证一个项目内集数序号不重复。
    """

    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="章节 ID")
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False, comment="章节序号（项目内唯一）")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="章节标题")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="章节摘要")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="章节原文（未清洗/可较长）")
    condensed_text: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="由模型精简后的原文（用于抽取/提示词）")
    storyboard_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="分镜数量")
    status: Mapped[ChapterStatus] = mapped_column(
        String(32),
        nullable=False,
        default=ChapterStatus.draft,
        comment="章节状态",
    )

    project: Mapped["Project"] = relationship(back_populates="chapters")
    shots: Mapped[list["Shot"]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("project_id", "index", name="uq_chapters_project_index"),
        Index("ix_chapters_updated_at", "updated_at"),
        Index("ix_chapters_status", "status"),
        Index("ix_chapters_project_title", "project_id", "title"),
    )


class ProjectActorLink(Base, TimestampMixin):
    """项目/章节/镜头 -> 演员关联。"""

    __tablename__ = "project_actor_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="关联行 ID")
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="项目 ID",
    )
    chapter_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="章节 ID",
    )
    shot_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("shots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="镜头 ID",
    )
    actor_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("actors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="演员 ID",
    )

    project: Mapped["Project"] = relationship(back_populates="actor_links")
    shot: Mapped["Shot"] = relationship(back_populates="actor_links")
    actor: Mapped["Actor"] = relationship()

    __table_args__ = (
        UniqueConstraint("actor_id", "project_id", "chapter_id", "shot_id", name="uq_project_actor_links_actor_scope"),
    )


class ProjectSceneLink(Base, TimestampMixin):
    """项目/章节/镜头 -> 场景关联。"""

    __tablename__ = "project_scene_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="关联行 ID")
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True, comment="项目 ID")
    chapter_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True, index=True, comment="章节 ID")
    shot_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("shots.id", ondelete="SET NULL"), nullable=True, index=True, comment="镜头 ID")
    scene_id: Mapped[str] = mapped_column(String(64), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True, comment="场景 ID")

    project: Mapped["Project"] = relationship(back_populates="scene_links")
    shot: Mapped["Shot"] = relationship(back_populates="scene_links")
    scene: Mapped["Scene"] = relationship()

    __table_args__ = (
        UniqueConstraint("scene_id", "project_id", "chapter_id", "shot_id", name="uq_project_scene_links_scene_scope"),
    )


class ProjectPropLink(Base, TimestampMixin):
    """项目/章节/镜头 -> 道具关联。"""

    __tablename__ = "project_prop_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="关联行 ID")
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True, comment="项目 ID")
    chapter_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True, index=True, comment="章节 ID")
    shot_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("shots.id", ondelete="SET NULL"), nullable=True, index=True, comment="镜头 ID")
    prop_id: Mapped[str] = mapped_column(String(64), ForeignKey("props.id", ondelete="CASCADE"), nullable=False, index=True, comment="道具 ID")

    project: Mapped["Project"] = relationship(back_populates="prop_links")
    shot: Mapped["Shot"] = relationship(back_populates="prop_links")
    prop: Mapped["Prop"] = relationship()

    __table_args__ = (
        UniqueConstraint("prop_id", "project_id", "chapter_id", "shot_id", name="uq_project_prop_links_prop_scope"),
    )


class ProjectCostumeLink(Base, TimestampMixin):
    """项目/章节/镜头 -> 服装关联。"""

    __tablename__ = "project_costume_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="关联行 ID")
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True, comment="项目 ID")
    chapter_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True, index=True, comment="章节 ID")
    shot_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("shots.id", ondelete="SET NULL"), nullable=True, index=True, comment="镜头 ID")
    costume_id: Mapped[str] = mapped_column(String(64), ForeignKey("costumes.id", ondelete="CASCADE"), nullable=False, index=True, comment="服装 ID")

    project: Mapped["Project"] = relationship(back_populates="costume_links")
    shot: Mapped["Shot"] = relationship(back_populates="costume_links")
    costume: Mapped["Costume"] = relationship()

    __table_args__ = (
        UniqueConstraint("costume_id", "project_id", "chapter_id", "shot_id", name="uq_project_costume_links_costume_scope"),
    )


class ProjectStyleOption(Base, TimestampMixin):
    """风格目录（可由用户自行维护）。

    为什么单独建表而不是继续用枚举：枚举无法在运行时新增，
    而「真人都市」「水墨画」这类风格在业务上会持续扩展（新题材、新画风），
    每次加风格都改代码发版不现实。枚举保留为内置种子的来源，表才是运行时事实。

    约束：同一个画面表现形式下风格名唯一——项目创建时的校验依赖这一点。
    """

    __tablename__ = "project_styles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="风格 ID")
    visual_style: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True, comment="所属画面表现形式（现实/动漫…）"
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="风格名称（如 真人都市）")
    description: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="面向用户的说明（会展示在管理页与新建弹窗）"
    )
    prompt_pack: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="提示词质感描述；为空时回落到内置风格包",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="同组内排序，越小越前")

    __table_args__ = (
        UniqueConstraint("visual_style", "name", name="uq_project_styles_visual_name"),
    )


__all__ = [
    "Project",
    "ProjectStyleOption",
    "Chapter",
    "ProjectActorLink",
    "ProjectSceneLink",
    "ProjectPropLink",
    "ProjectCostumeLink",
]
