"""P3 / C5：剧本文档与版本的请求响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScriptDocumentVersionRead(BaseModel):
    """文档版本摘要（不含大段原文）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version_no: int
    file_id: str | None = None
    file_name: str = ""
    file_type: str = ""
    content_hash: str = ""
    text_length: int = 0
    status: str = "candidate"
    parse_status: str = "not_parsed"
    extract_meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class ScriptDocumentRead(BaseModel):
    """剧本文档及其版本摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    chapter_id: str | None = None
    doc_type: str
    title: str = ""
    current_version_id: str | None = None
    active_version_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    versions: list[ScriptDocumentVersionRead] = Field(default_factory=list)
    current_version: ScriptDocumentVersionRead | None = None
    active_version: ScriptDocumentVersionRead | None = None


class ScriptDocumentListRead(BaseModel):
    """项目下的全部剧本文档。"""

    items: list[ScriptDocumentRead] = Field(default_factory=list)


class ScriptDocumentVersionDetailRead(ScriptDocumentVersionRead):
    """单版本完整原文，用于并排审核与证据定位。"""

    raw_text: str = ""


class ScriptDocumentUploadRead(BaseModel):
    """上传结果。``created=false`` 表示同内容重复上传，未新增版本。"""

    document: ScriptDocumentRead
    version: ScriptDocumentVersionRead
    created: bool
    warnings: list[str] = Field(default_factory=list)
