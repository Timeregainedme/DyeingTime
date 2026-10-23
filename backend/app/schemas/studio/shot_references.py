"""P6 / C11：参考绑定、@ 引用与生成快照 schemas。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ReferenceRole = Literal[
    "character_identity",
    "character_appearance",
    "scene",
    "prop",
    "costume",
    "shot_composition",
    "previous_shot",
]


class ReferenceBindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shot_id: str
    file_id: str | None = None
    file_url: str = ""
    asset_type: str = "shot_reference"
    asset_id: str | None = None
    asset_name: str = ""
    asset_version_id: str | None = None
    reference_role: str = "shot_composition"
    source: str = "auto"
    sort_order: int = 0
    is_pinned: bool = False
    is_active: bool = True


class ReferenceBindingUpdate(BaseModel):
    reference_role: ReferenceRole | None = None
    is_pinned: bool | None = None
    is_active: bool | None = None


class ReferenceBindingReorder(BaseModel):
    binding_ids: list[int] = Field(..., min_length=1)


class PromptReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    asset_type: str
    asset_id: str
    asset_name: str = ""
    asset_version_id: str | None = None
    mention: str = ""
    start_index: int | None = None
    end_index: int | None = None


class PromptResolveRequest(BaseModel):
    prompt: str = ""


class PromptResolveRead(BaseModel):
    prompt: str
    resolved: list[PromptReferenceRead] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ShotPromptUpdate(BaseModel):
    prompt: str = ""


class GenerationSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shot_id: str
    project_id: str
    chapter_id: str
    scene_group_id: str | None = None
    task_id: str | None = None
    model_id: str | None = None
    model_name: str = ""
    provider_name: str = ""
    reference_mode: str
    manifest: list[dict[str, Any]] = Field(default_factory=list)
    prompt: str
    natural_prompt: str = ""
    advanced_prompt: str = ""
    prompt_refs: list[dict[str, Any]] = Field(default_factory=list)
    audio_refs: list[dict[str, Any]] = Field(default_factory=list)
    asset_versions: list[dict[str, Any]] = Field(default_factory=list)
    generation_params: dict[str, Any] = Field(default_factory=dict)
    style_snapshot: dict[str, Any] = Field(default_factory=dict)
    duration: int = 0
    ratio: str = ""
    resolution: str | None = None
    input_hash: str = ""
    created_at: datetime | None = None


class GenerationPreviewRead(BaseModel):
    shot_id: str
    reference_mode: str = "reference"
    manifest: list[ReferenceBindingRead] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    audio_file_ids: list[str] = Field(default_factory=list)
    prompt: str = ""
    natural_prompt: str = ""
    advanced_prompt: str = ""
    prompt_refs: list[PromptReferenceRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_errors: list[str] = Field(default_factory=list)
    model_name: str = ""
    provider_name: str = ""
    ratio: str = ""
    resolution: str | None = None
    duration: int = 0
    input_hash: str = ""
    ir: dict[str, Any] = Field(default_factory=dict)


class P6VideoGenerateRequest(BaseModel):
    prompt: str = Field("", description="自然语言 @ 引用提示词")
    advanced_prompt: str = Field("", description="高级最终 H3 提示词；非空时优先")
    reference_mode: Literal["reference", "text_only"] = "reference"
    ratio: str | None = None
    resolution: str | None = None
    reference_audio_file_ids: list[str] = Field(default_factory=list)
    auto_adopt: bool = Field(False, description="生成完成后是否自动采纳；P6 默认显式采纳")


class P6VideoTaskCreated(BaseModel):
    task_id: str
    snapshot_id: str
    preview: GenerationPreviewRead
