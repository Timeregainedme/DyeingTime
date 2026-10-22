"""P2：项目生成配置与模型快照的请求/响应模型。

设计原则：
- 只暴露模型 ID、名称、供应商信息与能力参数；
- 不包含 API Key、Base URL 或任何凭据；
- `snapshot` 是确认时的只读审计副本，不能由客户端回写。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GenerationModelOptionRead(BaseModel):
    """项目可选模型及其能力摘要。"""

    id: str
    name: str
    category: str
    provider_id: str
    provider_name: str
    provider_key: str = ""
    provider_status: str = ""
    available: bool = Field(..., description="模型类别与供应商是否都可用")
    unavailable_reason: str = ""

    # 视频 / 图片通用能力
    allowed_ratios: list[str] = Field(default_factory=list)
    default_ratio: str | None = None
    allowed_resolutions: list[str] = Field(default_factory=list)
    default_resolution: str | None = None
    ratio_size_profiles: dict[str, dict[str, str]] = Field(default_factory=dict)
    default_resolution_profile: str | None = None
    min_seconds: int | None = None
    max_seconds: int | None = None

    # 音频能力
    supported_formats: list[str] = Field(default_factory=list)
    supports_voice: bool = False
    supports_custom_voice: bool = False
    supports_speed: bool = False
    supports_emotion: bool = False


class GenerationBusinessPolicyRead(BaseModel):
    """内部生产业务约束（与供应商能力分开）。"""

    duration_min: int
    duration_max: int
    default_shot_duration: int
    default_concurrency: int
    max_concurrency: int
    default_reference_mode: str
    allowed_reference_modes: list[str]
    use_dialog_audio_as_reference_default: bool


class ProjectGenerationOptionsRead(BaseModel):
    """项目配置面板所需的模型清单、全局默认与业务约束。"""

    image_models: list[GenerationModelOptionRead] = Field(default_factory=list)
    video_models: list[GenerationModelOptionRead] = Field(default_factory=list)
    audio_models: list[GenerationModelOptionRead] = Field(default_factory=list)
    global_defaults: dict[str, str | None] = Field(default_factory=dict)
    business: GenerationBusinessPolicyRead


class ProjectGenerationConfigCheck(BaseModel):
    """配置检查项；与 shot.status / 任务状态 / 视频准备度无关。"""

    key: str
    label: str
    ok: bool
    message: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)


class EffectiveGenerationModelRead(BaseModel):
    """某个类别当前实际生效的模型。"""

    category: str
    model_id: str | None = None
    model_name: str | None = None
    provider_id: str | None = None
    provider_name: str | None = None
    provider_key: str | None = None
    provider_status: str | None = None
    source: str = Field("missing", description="project / global / missing")
    available: bool = False
    reason: str = ""


class ProjectGenerationOutputRead(BaseModel):
    """输出规格的生效值与可选项。"""

    video_ratio: str | None = None
    video_resolution: str | None = None
    image_ratio: str | None = None
    image_resolution_profile: str | None = None
    video_ratios: list[str] = Field(default_factory=list)
    video_resolutions: list[str] = Field(default_factory=list)
    image_ratios: list[str] = Field(default_factory=list)
    image_resolution_profiles: list[str] = Field(default_factory=list)


class ProjectGenerationPolicyRead(BaseModel):
    """生成策略的生效值。"""

    reference_mode: str
    video_concurrency: int
    max_concurrency: int
    default_shot_duration: int
    duration_min: int
    duration_max: int
    provider_duration_min: int | None = None
    provider_duration_max: int | None = None
    use_dialog_audio_as_reference: bool


class ProjectGenerationConfigRead(BaseModel):
    """项目生成配置的完整只读视图。"""

    project_id: str
    confirmed: bool
    initialized: bool
    version: int
    confirmed_at: datetime | None = None
    updated_at: datetime | None = None
    image_model: EffectiveGenerationModelRead
    video_model: EffectiveGenerationModelRead
    audio_model: EffectiveGenerationModelRead
    output: ProjectGenerationOutputRead
    policy: ProjectGenerationPolicyRead
    checks: list[ProjectGenerationConfigCheck] = Field(default_factory=list)
    snapshot: dict[str, Any] | None = None


class ProjectGenerationConfigUpdate(BaseModel):
    """保存项目生成配置。

    `confirm=true` 时写入快照并递增版本；`confirm=false` 只保存草稿。
    模型字段显式传 null 表示清除项目覆盖、回退全局默认。
    """

    default_image_model_id: str | None = None
    default_video_model_id: str | None = None
    default_audio_model_id: str | None = None
    default_video_ratio: str | None = None
    default_video_resolution: str | None = None
    default_image_ratio: str | None = None
    default_image_resolution_profile: str | None = None
    default_shot_duration: int | None = Field(None, ge=1, le=60)
    video_duration_min: int | None = Field(None, ge=1, le=60)
    video_duration_max: int | None = Field(None, ge=1, le=60)
    video_concurrency: int | None = Field(None, ge=1, le=16)
    default_reference_mode: str | None = None
    use_dialog_audio_as_reference: bool | None = None
    confirm: bool = Field(True, description="是否确认并写入配置快照")
