"""P4：角色档案、资产版本、图片候选与音色绑定 schemas。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AssetType = Literal["character", "scene", "prop", "costume"]
ViewAngle = Literal["front", "left", "right", "back", "three_quarter"]
VersionKind = Literal["identity", "appearance", "base", "derived"]
VariantType = Literal[
    "base", "costume", "hairstyle", "makeup", "age", "weather", "lighting", "other"
]


class CharacterAliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alias: str
    normalized_alias: str
    source: str = "manual"


class CharacterAliasCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=255)


class CharacterAliasUpdate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=255)


class AssetVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    asset_type: str
    asset_id: str
    version_no: int
    parent_version_id: str | None = None
    version_kind: str
    variant_type: str
    name: str = ""
    description: str = ""
    attributes: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"
    status: str = "draft"
    created_at: datetime | None = None
    adopted_image_count: int = 0


class AssetImageCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: str
    asset_type: str
    asset_id: str
    asset_version_id: str | None = None
    candidate_batch_id: str
    view_angle: str
    quality_level: str
    file_id: str | None = None
    file_url: str = ""
    source: str = "generated"
    generation_task_id: str | None = None
    prompt: str = ""
    generation_params: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    width: int | None = None
    height: int | None = None
    format: str = "png"
    is_adopted: bool = False
    adopted_at: datetime | None = None
    adopted_by: int | None = None
    created_at: datetime | None = None


class AssetProfileUpdate(BaseModel):
    """更新角色圣经/资产文字字段；锁定后的身份核心字段由服务端拒绝。"""

    name: str | None = None
    description: str | None = None
    age_range: str | None = None
    appearance: str | None = None
    face_features: str | None = None
    body_type: str | None = None
    identity_features: str | None = None
    tags: list[str] | None = None
    costume_id: str | None = None
    actor_id: str | None = None


class AssetProfileRead(BaseModel):
    project_id: str
    asset_type: str
    asset_id: str
    name: str
    description: str = ""
    style: str = ""
    visual_style: str = ""
    tags: list[str] = Field(default_factory=list)
    thumbnail: str = ""
    current_version_id: str | None = None
    versions: list[AssetVersionRead] = Field(default_factory=list)
    candidates: list[AssetImageCandidateRead] = Field(default_factory=list)
    # 角色专属
    age_range: str = ""
    appearance: str = ""
    face_features: str = ""
    body_type: str = ""
    identity_features: str = ""
    aliases: list[CharacterAliasRead] = Field(default_factory=list)
    identity_version_id: str | None = None
    current_appearance_version_id: str | None = None
    identity_locked_at: datetime | None = None
    identity_lock_version: int = 0
    identity_locked: bool = False
    voice_id: str | None = None
    voice_source: str | None = None
    voice_description: str = ""
    effective_voice_id: str | None = None
    effective_voice_source: str | None = None
    voice_bound_at: datetime | None = None


class GenerateCandidatesRequest(BaseModel):
    """默认一次生成两张；不提供无界重试。"""

    view_angle: ViewAngle = "front"
    candidate_count: int = Field(2, ge=1, le=2)
    prompt: str | None = Field(None, description="可选：覆盖资产图提示词")


class CreateDerivedVersionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    variant_type: VariantType = "other"
    parent_version_id: str | None = None
    costume_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    activate: bool = True


class SwitchVersionRequest(BaseModel):
    version_id: str
    expected_lock_version: int | None = Field(
        None, description="角色身份并发检查；不匹配返回 409"
    )


class CharacterLockRequest(BaseModel):
    expected_lock_version: int | None = None


class VoiceBindingUpdate(BaseModel):
    voice_id: str | None = None
    voice_source: str | None = Field(None, description="preset / custom")
    voice_description: str | None = None


class VoiceBindingRead(BaseModel):
    character_id: str
    voice_id: str | None = None
    voice_source: str | None = None
    voice_description: str = ""
    bound_at: datetime | None = None
    actor_id: str | None = None
    actor_voice_id: str | None = None
    actor_voice_source: str | None = None
    effective_voice_id: str | None = None
    effective_voice_source: str | None = None
    effective_from: str = "unbound"


class CandidateAdoptRequest(BaseModel):
    version_id: str | None = Field(None, description="可选：指定要采纳到的版本")
    make_primary: bool = Field(True, description="是否同步为资产图片槽位主图")


class AssetImpactShot(BaseModel):
    shot_id: str
    chapter_id: str
    chapter_index: int | None = None
    chapter_title: str = ""
    shot_index: int | None = None
    shot_title: str = ""
    certainty: str = "possible"
    reference_kind: str = "possible"
    version_precision: str = "asset_level"
    has_video: bool = False
    video_file_id: str | None = None


class AssetImpactRead(BaseModel):
    project_id: str
    asset_type: str
    asset_id: str
    from_version_id: str | None = None
    to_version_id: str | None = None
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    shots: list[AssetImpactShot] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class AssetVersionImpactRefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: str
    asset_type: str
    asset_id: str
    from_version_id: str | None = None
    to_version_id: str | None = None
    shot_id: str
    chapter_id: str
    certainty: str
    reference_kind: str
    had_video: bool = False
    created_at: datetime | None = None
