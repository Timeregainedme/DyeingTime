"""Studio 域与生成任务（GenerationTask）的关联表（方案 B：分表强外键）。

设计目标：
- 不污染 `GenerationTask`（保持 task 模块独立）
- 由 studio 域维护关联关系（Project/Chapter/Shot -> GenerationTask）
- 数据库层面强约束：外键确保引用存在；删除业务对象或任务时自动级联清理关联
"""

from __future__ import annotations

from enum import Enum

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class GenerationTaskLinkStatus(str, Enum):
    """生成任务关联状态。"""

    accepted = "accepted"  # 已采用
    todo = "todo"  # 待操作
    rejected = "rejected"  # 未采用


class GenerationTaskLink(Base, TimestampMixin):
    """通用的生成任务关联表。

    通过 resource_type + relation_type + relation_entity_id 表示与上层业务资源的关联：
    - resource_type：生成资源类型，如 image / video / text
    - relation_type：业务类型，如 prop / costume / scene / shot_first_frame_prompt 等
    - relation_entity_id：具体业务实体 ID，如某个 prop/costume/scene/shot 的主键
    """

    __tablename__ = "generation_task_links"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="关联行 ID",
    )
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("generation_tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="生成任务 ID",
    )
    resource_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="",
        comment="生成资源类型（如 image/video/text）",
    )
    relation_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="",
        comment="业务类型（如 prop/costume/scene 等）",
    )
    relation_entity_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
        comment="关联业务实体 ID（如具体的 prop/costume/scene/shot 等对象 ID）",
    )
    file_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联产物文件 ID（files.id；适用于图片/音频/视频）",
    )
    status: Mapped[GenerationTaskLinkStatus] = mapped_column(
        String(32),
        nullable=False,
        default=GenerationTaskLinkStatus.todo,
        comment="关联状态：accepted=已采用、todo=待操作、rejected=未采用",
    )

    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "resource_type",
            "relation_type",
            "relation_entity_id",
            name="uq_task_resource_relation_entity",
        ),
        Index(
            "ix_task_link_task_id_resource",
            "task_id",
            "resource_type",
        ),
        Index(
            "ix_task_link_relation_entity",
            "relation_type",
            "relation_entity_id",
        ),
        Index("ix_task_link_file_id", "file_id"),
        Index(
            "ix_task_link_status_updated_at",
            "status",
            "updated_at",
        ),
    )

