"""P2 / C4：风格分析、项目风格选择与锁定快照的请求/响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.studio.projects import (
    ProjectStyleOptionRead,
    StyleStructuredProfile,
)


class StyleAnalysisCapabilityRead(BaseModel):
    """AI 风格分析是否可用。"""

    available: bool
    model_id: str | None = None
    model_name: str | None = None
    provider_name: str | None = None
    reason: str = ""


class StyleAnalysisRequest(BaseModel):
    """分析 1–3 张风格参考图；不落库。"""

    file_ids: list[str] = Field(..., min_length=1, max_length=3, description="风格参考图文件 ID")
    model_id: str | None = Field(None, description="可选文本/视觉模型 ID；默认使用全局文本模型")


class StyleAnalysisRead(BaseModel):
    """AI 输出的结构化风格字段；可直接保存为草稿。"""

    profile: StyleStructuredProfile
    prompt_pack: str
    model_id: str
    model_name: str
    provider_name: str
    image_count: int


class ProjectStyleSnapshotRead(BaseModel):
    """锁定快照；与全局风格目录解耦。"""

    model_config = {"from_attributes": True}

    project_id: str
    source_style_id: str | None = None
    style_name: str
    visual_style: str
    description: str
    structured_profile: StyleStructuredProfile | None = None
    prompt_pack: str
    reference_file_ids: list[str] = Field(default_factory=list)
    sample_file_ids: list[str] = Field(default_factory=list)
    snapshot_version: int
    locked_at: datetime

    @field_validator("reference_file_ids", "sample_file_ids", mode="before")
    @classmethod
    def _none_to_empty_list(cls, value: object) -> object:
        return value or []


class ProjectStyleStateRead(BaseModel):
    """项目风格面板的完整状态。"""

    project_id: str
    locked: bool
    style: ProjectStyleOptionRead | None = None
    snapshot: ProjectStyleSnapshotRead | None = None
    styles: list[ProjectStyleOptionRead] = Field(default_factory=list)
    visual_styles: list[str] = Field(default_factory=list)


class ProjectStyleSelectRequest(BaseModel):
    """选择风格（未锁定前的草稿选择）。"""

    style_id: str


class ProjectStyleLockRequest(BaseModel):
    """锁定风格；不传 style_id 时使用当前选择。"""

    style_id: str | None = None
    sample_file_ids: list[str] = Field(
        default_factory=list, max_length=3, description="确认样张文件 ID（最多 3 张）"
    )
