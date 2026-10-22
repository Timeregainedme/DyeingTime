"""P3 / C5：剧本文档与版本模型。

设计目标：
- 原始上传文件保存在 `files`（FileItem.type=document），
- 提取后的原文保存在版本表，保留完整历史；
- `chapters.raw_text` 继续作为正式章节正文，只有用户显式启用版本（或 C6 审核确认）才同步；
- `current_version_id` 指向最近上传的候选版本，`active_version_id` 指向当前生效版本，
  二者分离，保证「上传候选」不会立刻覆盖已确认内容。
"""

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


class ScriptDocument(Base, TimestampMixin):
    """项目级世界观文档或某一集的剧本文件。"""

    __tablename__ = "script_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="文档 ID")
    project_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属项目 ID",
    )
    chapter_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="所属章节 ID；世界观文档为空",
    )
    doc_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="文档类型：worldbuilding / episode",
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", comment="展示标题"
    )
    # 不建外键：current/active 指向版本表，而版本表又引用文档，避免循环依赖。
    current_version_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="最近上传的版本 ID（候选或生效）"
    )
    active_version_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="当前生效版本 ID；为空表示尚未生效"
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="上传者账号 ID",
    )

    versions: Mapped[list["ScriptDocumentVersion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ScriptDocumentVersion.version_no",
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id", "chapter_id", "doc_type", name="uq_script_documents_scope"
        ),
        Index("ix_script_documents_project_type", "project_id", "doc_type"),
    )


class ScriptDocumentVersion(Base, TimestampMixin):
    """一次上传形成的不可变文档版本。"""

    __tablename__ = "script_document_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="版本 ID")
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("script_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属文档 ID",
    )
    version_no: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="版本号，从 1 开始递增"
    )
    file_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="原始上传文件 ID（FileItem.type=document）",
    )
    file_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", comment="原始文件名"
    )
    file_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="", comment="文件类型：docx / md"
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, default="", comment="原始文件 SHA-256"
    )
    raw_text: Mapped[str] = mapped_column(
        Text, nullable=False, default="", comment="提取后的完整原文"
    )
    text_length: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="原文长度（字符）"
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="candidate",
        comment="版本状态：candidate / active / superseded",
    )
    parse_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="not_parsed",
        comment="解析状态：not_parsed / parsing / parsed / failed",
    )
    # 列名保留 metadata，属性名避开 SQLAlchemy Declarative 的 metadata。
    extract_meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        comment="提取告警、表格/图片统计等非敏感元数据",
    )
    created_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="上传者账号 ID",
    )

    document: Mapped["ScriptDocument"] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("document_id", "version_no", name="uq_script_document_versions_no"),
        Index("ix_script_document_versions_hash", "content_hash"),
    )


__all__ = ["ScriptDocument", "ScriptDocumentVersion"]
