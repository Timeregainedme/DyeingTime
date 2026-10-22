"""P2：项目级生成配置、模型快照与能力校验。

为什么需要这一层：
- 全局 `ModelSettings` 只回答「平台默认用什么」，无法回答「这个项目已确认用什么」。
  直接读全局默认会让「改全局默认」静默影响进行中的项目。
- 项目配置必须在服务端校验供应商能力（比例、分辨率、时长），不能只靠前端下拉。

安全边界：
- 快照只保存模型 ID / 名称 / 供应商 ID / 能力参数；
- API Key、Base URL 等凭据一律不进入快照，运行时由 provider 解析。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.integrations.audio_capabilities import resolve_audio_capability
from app.core.integrations.image_capabilities import resolve_image_capability
from app.core.integrations.video_capabilities import resolve_video_capability
from app.models.llm import Model, ModelCategoryKey, ModelSettings, Provider, ProviderStatus
from app.models.studio import Project
from app.models.studio import ProjectStyleSnapshot
from app.schemas.studio.project_generation import (
    EffectiveGenerationModelRead,
    GenerationBusinessPolicyRead,
    GenerationModelOptionRead,
    ProjectGenerationConfigCheck,
    ProjectGenerationConfigRead,
    ProjectGenerationConfigUpdate,
    ProjectGenerationOptionsRead,
    ProjectGenerationOutputRead,
    ProjectGenerationPolicyRead,
)
from app.services.llm.provider_registry import resolve_provider_key_from_name

# 内部生产业务约束：与供应商能力（H3 4–30 秒）分开，P2 不允许擅自扩大。
BUSINESS_DURATION_MIN = 4
BUSINESS_DURATION_MAX = 15
DEFAULT_SHOT_DURATION = 5
DEFAULT_CONCURRENCY = 4
MAX_CONCURRENCY = 16
DEFAULT_REFERENCE_MODE = "reference"
ALLOWED_REFERENCE_MODES = ("reference",)
SNAPSHOT_SCHEMA_VERSION = 1
CAPABILITY_SNAPSHOT_VERSION = "p2-2026-10"

_CATEGORY_LABELS = {
    ModelCategoryKey.image: "图片",
    ModelCategoryKey.video: "视频",
    ModelCategoryKey.audio: "音频",
}


def _settings_model_id(settings: ModelSettings | None, category: ModelCategoryKey) -> str | None:
    if settings is None:
        return None
    if category == ModelCategoryKey.image:
        return settings.default_image_model_id
    if category == ModelCategoryKey.video:
        return settings.default_video_model_id
    if category == ModelCategoryKey.audio:
        return settings.default_audio_model_id
    return None


def _project_model_id(project: Project, category: ModelCategoryKey) -> str | None:
    if category == ModelCategoryKey.image:
        return project.default_image_model_id
    if category == ModelCategoryKey.video:
        return project.default_video_model_id
    if category == ModelCategoryKey.audio:
        return project.default_audio_model_id
    return None


def _set_project_model_id(project: Project, category: ModelCategoryKey, model_id: str | None) -> None:
    if category == ModelCategoryKey.image:
        project.default_image_model_id = model_id
    elif category == ModelCategoryKey.video:
        project.default_video_model_id = model_id
    elif category == ModelCategoryKey.audio:
        project.default_audio_model_id = model_id


def _provider_key(provider: Provider | None) -> str:
    if provider is None:
        return ""
    try:
        return resolve_provider_key_from_name(provider.name)
    except Exception:  # noqa: BLE001 - 未登记的供应商只影响可用性，不应炸掉配置页
        return ""


def _enum_text(value: Any) -> str:
    """str Enum 在 Python 3.11 下 str(x) 可能返回 'Class.member'，统一取 value。"""
    return str(getattr(value, "value", value) or "")


def _video_capability(provider_key: str, model_name: str):
    if not provider_key:
        return None
    try:
        return resolve_video_capability(provider=provider_key, model=model_name)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return None


def _image_capability(provider_key: str, model_name: str):
    if not provider_key:
        return None
    try:
        return resolve_image_capability(provider=provider_key, model=model_name)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return None


def _audio_capability(provider_key: str, model_name: str):
    if not provider_key:
        return None
    try:
        return resolve_audio_capability(provider=provider_key, model=model_name)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return None


def _sorted_values(values: set[str] | None) -> list[str]:
    return sorted(values or [])


def _model_option(
    model: Model,
    provider: Provider,
    *,
    category: ModelCategoryKey,
) -> GenerationModelOptionRead:
    """把模型 + 供应商 + 能力收敛成配置面板可用的选项。"""
    provider_key = _provider_key(provider)
    available = model.category == category.value and provider.status == ProviderStatus.active and bool(provider_key)
    reason = ""
    if model.category != category.value:
        reason = f"模型类别不是 {category.value}"
    elif provider.status != ProviderStatus.active:
        reason = f"供应商状态为 {provider.status}"
    elif not provider_key:
        reason = f"供应商「{provider.name}」未被适配器识别"

    option = GenerationModelOptionRead(
        id=model.id,
        name=model.name,
        category=model.category,
        provider_id=provider.id,
        provider_name=provider.name,
        provider_key=provider_key,
        provider_status=_enum_text(provider.status),
        available=available,
        unavailable_reason=reason,
    )

    if category == ModelCategoryKey.video:
        cap = _video_capability(provider_key, model.name)
        if cap is not None:
            option.allowed_ratios = _sorted_values(cap.allowed_ratios)
            option.default_ratio = cap.default_ratio
            option.allowed_resolutions = _sorted_values(cap.allowed_resolutions)
            option.default_resolution = cap.default_resolution
            option.min_seconds = cap.min_seconds
            option.max_seconds = cap.max_seconds
    elif category == ModelCategoryKey.image:
        cap = _image_capability(provider_key, model.name)
        if cap is not None:
            option.allowed_ratios = _sorted_values(cap.supported_ratios)
            option.ratio_size_profiles = cap.ratio_size_profiles or {}
            if not option.allowed_ratios:
                option.allowed_ratios = sorted(option.ratio_size_profiles.keys())
            option.default_resolution_profile = cap.default_resolution_profile
    else:
        cap = _audio_capability(provider_key, model.name)
        if cap is not None:
            option.supported_formats = _sorted_values(cap.supported_formats)
            option.supports_voice = cap.supports_voice
            option.supports_custom_voice = cap.supports_custom_voice
            option.supports_speed = cap.supports_speed
            option.supports_emotion = cap.supports_emotion

    return option


async def list_project_generation_options(db: AsyncSession) -> ProjectGenerationOptionsRead:
    """列出可配置的图片 / 视频 / 音频模型与全局默认。"""
    rows = (
        await db.execute(
            select(Model, Provider)
            .join(Provider, Provider.id == Model.provider_id)
            .where(Model.category.in_([ModelCategoryKey.image.value, ModelCategoryKey.video.value, ModelCategoryKey.audio.value]))
            .order_by(Model.category.asc(), Model.name.asc())
        )
    ).all()

    image_models: list[GenerationModelOptionRead] = []
    video_models: list[GenerationModelOptionRead] = []
    audio_models: list[GenerationModelOptionRead] = []
    for model, provider in rows:
        try:
            category = ModelCategoryKey(model.category)
        except ValueError:
            continue
        option = _model_option(model, provider, category=category)
        if category == ModelCategoryKey.image:
            image_models.append(option)
        elif category == ModelCategoryKey.video:
            video_models.append(option)
        elif category == ModelCategoryKey.audio:
            audio_models.append(option)

    settings = await db.get(ModelSettings, 1)
    return ProjectGenerationOptionsRead(
        image_models=image_models,
        video_models=video_models,
        audio_models=audio_models,
        global_defaults={
            "image_model_id": settings.default_image_model_id if settings else None,
            "video_model_id": settings.default_video_model_id if settings else None,
            "audio_model_id": settings.default_audio_model_id if settings else None,
        },
        business=GenerationBusinessPolicyRead(
            duration_min=BUSINESS_DURATION_MIN,
            duration_max=BUSINESS_DURATION_MAX,
            default_shot_duration=DEFAULT_SHOT_DURATION,
            default_concurrency=DEFAULT_CONCURRENCY,
            max_concurrency=MAX_CONCURRENCY,
            default_reference_mode=DEFAULT_REFERENCE_MODE,
            allowed_reference_modes=list(ALLOWED_REFERENCE_MODES),
            use_dialog_audio_as_reference_default=False,
        ),
    )


async def _resolve_model_state(
    db: AsyncSession,
    *,
    category: ModelCategoryKey,
    explicit_model_id: str | None,
    global_model_id: str | None,
) -> tuple[EffectiveGenerationModelRead, Model | None, Provider | None, Any]:
    """解析某类别实际模型；项目显式配置缺失时才回退全局默认。"""
    source = "project" if explicit_model_id else ("global" if global_model_id else "missing")
    model_id = explicit_model_id or global_model_id

    if not model_id:
        return (
            EffectiveGenerationModelRead(
                category=category.value,
                source="missing",
                available=False,
                reason=f"未配置{_CATEGORY_LABELS[category]}模型",
            ),
            None,
            None,
            None,
        )

    model = await db.get(Model, model_id)
    if model is None:
        return (
            EffectiveGenerationModelRead(
                category=category.value,
                model_id=model_id,
                source=source,
                available=False,
                reason=f"模型不存在：{model_id}",
            ),
            None,
            None,
            None,
        )

    provider = await db.get(Provider, model.provider_id)
    provider_key = _provider_key(provider)
    available = (
        model.category == category.value
        and provider is not None
        and provider.status == ProviderStatus.active
        and bool(provider_key)
    )
    reason = ""
    if model.category != category.value:
        reason = f"模型类别不匹配：{model.category} != {category.value}"
    elif provider is None:
        reason = "供应商不存在"
    elif provider.status != ProviderStatus.active:
        reason = f"供应商状态为 {provider.status}"
    elif not provider_key:
        reason = "供应商未被适配器识别"

    capability = None
    if category == ModelCategoryKey.video:
        capability = _video_capability(provider_key, model.name)
    elif category == ModelCategoryKey.image:
        capability = _image_capability(provider_key, model.name)
    elif category == ModelCategoryKey.audio:
        capability = _audio_capability(provider_key, model.name)

    return (
        EffectiveGenerationModelRead(
            category=category.value,
            model_id=model.id,
            model_name=model.name,
            provider_id=provider.id if provider else model.provider_id,
            provider_name=provider.name if provider else None,
            provider_key=provider_key or None,
            provider_status=_enum_text(provider.status) if provider else None,
            source=source,
            available=available,
            reason=reason,
        ),
        model,
        provider,
        capability,
    )


def _ratio_choices(capability: Any) -> list[str]:
    return _sorted_values(getattr(capability, "allowed_ratios", None)) if capability else []


def _image_ratio_choices(capability: Any) -> list[str]:
    if capability is None:
        return []
    ratios = _sorted_values(getattr(capability, "supported_ratios", None))
    if ratios:
        return ratios
    profiles = getattr(capability, "ratio_size_profiles", None) or {}
    return sorted(profiles.keys())


def _resolution_choices(capability: Any) -> list[str]:
    return _sorted_values(getattr(capability, "allowed_resolutions", None)) if capability else []


def _image_profile_choices(capability: Any) -> list[str]:
    if capability is None:
        return []
    profiles = getattr(capability, "ratio_size_profiles", None) or {}
    values: set[str] = set()
    for item in profiles.values():
        values.update(item.keys())
    default = getattr(capability, "default_resolution_profile", None)
    if default:
        values.add(default)
    return sorted(values)


def _build_snapshot(
    *,
    version: int,
    image: EffectiveGenerationModelRead,
    video: EffectiveGenerationModelRead,
    audio: EffectiveGenerationModelRead,
    image_capability: Any,
    video_capability: Any,
    audio_capability: Any,
    output: ProjectGenerationOutputRead,
    policy: ProjectGenerationPolicyRead,
) -> dict[str, Any]:
    """只含非敏感信息；任何 API Key / Base URL 都不允许进入。"""
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "capability_version": CAPABILITY_SNAPSHOT_VERSION,
        "confirmed_at": datetime.now(UTC).isoformat(),
        "version": version,
        "models": {
            "image": image.model_dump(),
            "video": video.model_dump(),
            "audio": audio.model_dump(),
        },
        "capabilities": {
            "image": {
                "ratios": _image_ratio_choices(image_capability),
                "resolution_profiles": _image_profile_choices(image_capability),
            },
            "video": {
                "ratios": _ratio_choices(video_capability),
                "resolutions": _resolution_choices(video_capability),
                "min_seconds": getattr(video_capability, "min_seconds", None),
                "max_seconds": getattr(video_capability, "max_seconds", None),
            },
            "audio": {
                "formats": _sorted_values(getattr(audio_capability, "supported_formats", None)),
                "supports_voice": getattr(audio_capability, "supports_voice", False),
                "supports_custom_voice": getattr(audio_capability, "supports_custom_voice", False),
            },
        },
        "output": output.model_dump(),
        "policy": policy.model_dump(),
    }


async def build_project_generation_config(
    db: AsyncSession,
    *,
    project_id: str,
    values: dict[str, Any],
    confirmed_at: datetime | None,
    version: int,
    snapshot: dict[str, Any] | None,
) -> ProjectGenerationConfigRead:
    """按给定值构建完整配置视图（不写库）。

    `values` 是「合并后的项目配置」，字段名与 Project 列一致；
    读接口传 ORM 当前值，保存接口传 patch 后的候选值，保证校验与预览同源。
    """
    settings = await db.get(ModelSettings, 1)
    image, _image_model, _image_provider, image_cap = await _resolve_model_state(
        db,
        category=ModelCategoryKey.image,
        explicit_model_id=values.get("default_image_model_id"),
        global_model_id=settings.default_image_model_id if settings else None,
    )
    video, _video_model, _video_provider, video_cap = await _resolve_model_state(
        db,
        category=ModelCategoryKey.video,
        explicit_model_id=values.get("default_video_model_id"),
        global_model_id=settings.default_video_model_id if settings else None,
    )
    audio, _audio_model, _audio_provider, audio_cap = await _resolve_model_state(
        db,
        category=ModelCategoryKey.audio,
        explicit_model_id=values.get("default_audio_model_id"),
        global_model_id=settings.default_audio_model_id if settings else None,
    )

    video_ratios = _ratio_choices(video_cap)
    video_resolutions = _resolution_choices(video_cap)
    image_ratios = _image_ratio_choices(image_cap)
    image_profiles = _image_profile_choices(image_cap)

    provider_min = getattr(video_cap, "min_seconds", None)
    provider_max = getattr(video_cap, "max_seconds", None)
    business_min = int(values.get("video_duration_min") or BUSINESS_DURATION_MIN)
    business_max = int(values.get("video_duration_max") or BUSINESS_DURATION_MAX)
    effective_min = max(provider_min or business_min, business_min)
    effective_max = min(provider_max or business_max, business_max)

    video_ratio = values.get("default_video_ratio") or getattr(video_cap, "default_ratio", None)
    if not video_ratio and video_ratios:
        video_ratio = video_ratios[0]
    video_resolution = values.get("default_video_resolution") or getattr(video_cap, "default_resolution", None)
    if not video_resolution and video_resolutions:
        video_resolution = video_resolutions[0]
    image_ratio = values.get("default_image_ratio") or values.get("default_video_ratio")
    if not image_ratio and image_ratios:
        image_ratio = image_ratios[0]
    image_profile = values.get("default_image_resolution_profile") or getattr(
        image_cap, "default_resolution_profile", None
    )
    if not image_profile and image_profiles:
        image_profile = image_profiles[0]

    output = ProjectGenerationOutputRead(
        video_ratio=video_ratio,
        video_resolution=video_resolution,
        image_ratio=image_ratio,
        image_resolution_profile=image_profile,
        video_ratios=video_ratios,
        video_resolutions=video_resolutions,
        image_ratios=image_ratios,
        image_resolution_profiles=image_profiles,
    )

    reference_mode = str(values.get("default_reference_mode") or DEFAULT_REFERENCE_MODE)
    concurrency = int(values.get("video_concurrency") or DEFAULT_CONCURRENCY)
    shot_duration = int(values.get("default_shot_duration") or DEFAULT_SHOT_DURATION)
    audio_reference = bool(values.get("use_dialog_audio_as_reference") or False)

    policy = ProjectGenerationPolicyRead(
        reference_mode=reference_mode,
        video_concurrency=concurrency,
        max_concurrency=MAX_CONCURRENCY,
        default_shot_duration=shot_duration,
        duration_min=effective_min,
        duration_max=effective_max,
        provider_duration_min=provider_min,
        provider_duration_max=provider_max,
        use_dialog_audio_as_reference=audio_reference,
    )

    checks: list[ProjectGenerationConfigCheck] = []

    def add(key: str, label: str, ok: bool, message: str = "", detail: dict[str, Any] | None = None) -> None:
        checks.append(
            ProjectGenerationConfigCheck(
                key=key, label=label, ok=ok, message=message, detail=detail or {}
            )
        )

    add(
        "image_model_ready",
        "图片模型可用",
        image.available,
        image.reason or "项目图片模型可使用",
        {"model_id": image.model_id, "source": image.source},
    )
    add(
        "video_model_ready",
        "视频模型可用",
        video.available,
        video.reason or "项目视频模型可使用",
        {"model_id": video.model_id, "source": video.source},
    )
    add(
        "audio_model_ready",
        "音频模型可用",
        audio.available,
        audio.reason or "项目音频模型可使用",
        {"model_id": audio.model_id, "source": audio.source},
    )
    video_ratio_ok = bool(video_ratio) and (not video_ratios or video_ratio in video_ratios)
    add(
        "video_ratio_ready",
        "视频比例有效",
        video_ratio_ok,
        f"视频比例 {video_ratio} 已验证" if video_ratio_ok else f"视频比例 {video_ratio or '未设置'} 不受当前视频模型支持",
        {"value": video_ratio, "allowed": video_ratios},
    )
    video_resolution_ok = bool(video_resolution) and (
        not video_resolutions or video_resolution in video_resolutions
    )
    add(
        "video_resolution_ready",
        "视频分辨率有效",
        video_resolution_ok,
        f"视频分辨率 {video_resolution} 已验证"
        if video_resolution_ok
        else f"视频分辨率 {video_resolution or '未设置'} 不受当前视频模型支持",
        {"value": video_resolution, "allowed": video_resolutions},
    )
    image_ratio_ok = bool(image_ratio) and (not image_ratios or image_ratio in image_ratios)
    add(
        "image_ratio_ready",
        "图片比例有效",
        image_ratio_ok,
        f"图片比例 {image_ratio} 已验证" if image_ratio_ok else f"图片比例 {image_ratio or '未设置'} 不受当前图片模型支持",
        {"value": image_ratio, "allowed": image_ratios},
    )
    image_profile_ok = bool(image_profile) and (
        not image_profiles or image_profile in image_profiles
    )
    add(
        "image_resolution_ready",
        "图片清晰度有效",
        image_profile_ok,
        f"图片档位 {image_profile} 已验证"
        if image_profile_ok
        else f"图片档位 {image_profile or '未设置'} 不受当前图片模型支持",
        {"value": image_profile, "allowed": image_profiles},
    )

    duration_ok = effective_min <= shot_duration <= effective_max
    add(
        "duration_ready",
        "默认时长有效",
        duration_ok,
        f"默认时长 {shot_duration}s 不在允许范围 {effective_min}–{effective_max}s"
        if not duration_ok
        else f"默认时长 {shot_duration}s 在允许范围 {effective_min}–{effective_max}s",
        {"value": shot_duration, "min": effective_min, "max": effective_max},
    )
    concurrency_ok = 1 <= concurrency <= MAX_CONCURRENCY
    add(
        "concurrency_ready",
        "并发数有效",
        concurrency_ok,
        f"并发数 {concurrency} 在 1–{MAX_CONCURRENCY} 之间"
        if concurrency_ok
        else f"并发数需在 1–{MAX_CONCURRENCY} 之间",
        {"value": concurrency},
    )
    mode_ok = reference_mode in ALLOWED_REFERENCE_MODES
    add(
        "reference_mode_ready",
        "参考模式有效",
        mode_ok,
        f"参考模式 {reference_mode} 已验证"
        if mode_ok
        else f"参考模式只支持 {', '.join(ALLOWED_REFERENCE_MODES)}",
        {"value": reference_mode},
    )

    style_snapshot = await db.get(ProjectStyleSnapshot, project_id)
    add(
        "style_locked",
        "视觉风格已锁定",
        style_snapshot is not None,
        "视觉风格尚未锁定；请在「风格圣经」面板确认并锁定"
        if style_snapshot is None
        else f"已锁定：{style_snapshot.style_name}",
        {"style_name": style_snapshot.style_name if style_snapshot else None},
    )

    required_keys = {
        "image_model_ready",
        "video_model_ready",
        "audio_model_ready",
        "video_ratio_ready",
        "video_resolution_ready",
        "image_ratio_ready",
        "image_resolution_ready",
        "duration_ready",
        "concurrency_ready",
        "reference_mode_ready",
    }
    configured = all(check.ok for check in checks if check.key in required_keys)
    initialized = configured and confirmed_at is not None and style_snapshot is not None

    return ProjectGenerationConfigRead(
        project_id=project_id,
        confirmed=confirmed_at is not None,
        initialized=initialized,
        version=version,
        confirmed_at=confirmed_at,
        updated_at=values.get("generation_config_updated_at"),
        image_model=image,
        video_model=video,
        audio_model=audio,
        output=output,
        policy=policy,
        checks=checks,
        snapshot=snapshot,
    )


def _project_values(project: Project) -> dict[str, Any]:
    return {
        "default_image_model_id": project.default_image_model_id,
        "default_video_model_id": project.default_video_model_id,
        "default_audio_model_id": project.default_audio_model_id,
        "default_video_ratio": project.default_video_ratio,
        "default_video_resolution": project.default_video_resolution,
        "default_image_ratio": project.default_image_ratio,
        "default_image_resolution_profile": project.default_image_resolution_profile,
        "default_shot_duration": project.default_shot_duration,
        "video_duration_min": project.video_duration_min,
        "video_duration_max": project.video_duration_max,
        "video_concurrency": project.video_concurrency,
        "default_reference_mode": project.default_reference_mode,
        "use_dialog_audio_as_reference": project.use_dialog_audio_as_reference,
        "generation_config_updated_at": project.generation_config_updated_at,
    }


async def get_project_generation_config(
    db: AsyncSession, *, project: Project
) -> ProjectGenerationConfigRead:
    """读取项目生成配置（未确认时也返回真实草稿值与检查结果）。"""
    return await build_project_generation_config(
        db,
        project_id=project.id,
        values=_project_values(project),
        confirmed_at=project.generation_config_confirmed_at,
        version=project.generation_config_version,
        snapshot=project.generation_config_snapshot,
    )


async def save_project_generation_config(
    db: AsyncSession,
    *,
    project: Project,
    body: ProjectGenerationConfigUpdate,
) -> ProjectGenerationConfigRead:
    """保存项目配置；`confirm=true` 时校验并写入快照。

    校验失败抛 ValueError（由全局 handler 转 400），不修改 ORM 对象。
    """
    patch = body.model_dump(exclude_unset=True, exclude={"confirm"})
    values = _project_values(project)
    values.update(patch)

    # 业务时长范围：固定 4–15，防止通过 API 擅自扩大到供应商上限。
    duration_min = int(values.get("video_duration_min") or BUSINESS_DURATION_MIN)
    duration_max = int(values.get("video_duration_max") or BUSINESS_DURATION_MAX)
    if duration_min < BUSINESS_DURATION_MIN or duration_max > BUSINESS_DURATION_MAX:
        raise ValueError(
            f"项目业务时长范围必须在 {BUSINESS_DURATION_MIN}–{BUSINESS_DURATION_MAX} 秒内"
        )
    if duration_min > duration_max:
        raise ValueError("视频时长下限不能大于上限")

    reference_mode = str(values.get("default_reference_mode") or DEFAULT_REFERENCE_MODE)
    if reference_mode not in ALLOWED_REFERENCE_MODES:
        raise ValueError(f"项目默认参考模式只支持：{', '.join(ALLOWED_REFERENCE_MODES)}")

    concurrency = int(values.get("video_concurrency") or DEFAULT_CONCURRENCY)
    if not 1 <= concurrency <= MAX_CONCURRENCY:
        raise ValueError(f"视频并发数需在 1–{MAX_CONCURRENCY} 之间")

    values["video_duration_min"] = duration_min
    values["video_duration_max"] = duration_max
    values["default_reference_mode"] = reference_mode
    values["video_concurrency"] = concurrency

    candidate = await build_project_generation_config(
        db,
        project_id=project.id,
        values=values,
        confirmed_at=project.generation_config_confirmed_at,
        version=project.generation_config_version,
        snapshot=project.generation_config_snapshot,
    )

    # 保存草稿允许不完整；确认必须是完整且可执行的配置。
    if body.confirm:
        # 风格锁定是独立的初始化步骤：配置可以先确认，initialize 仍需风格锁定。
        failed = [
            check
            for check in candidate.checks
            if not check.ok and check.key != "style_locked"
        ]
        if failed:
            raise ValueError(
                "配置未通过检查：" + "；".join(f"{item.label}（{item.message}）" for item in failed)
            )

    for field in (
        "default_image_model_id",
        "default_video_model_id",
        "default_audio_model_id",
        "default_video_ratio",
        "default_video_resolution",
        "default_image_ratio",
        "default_image_resolution_profile",
        "default_shot_duration",
        "video_duration_min",
        "video_duration_max",
        "video_concurrency",
        "default_reference_mode",
        "use_dialog_audio_as_reference",
    ):
        if field in patch:
            setattr(project, field, patch[field])

    project.video_duration_min = duration_min
    project.video_duration_max = duration_max
    project.default_reference_mode = reference_mode
    project.video_concurrency = concurrency
    project.generation_config_updated_at = datetime.now(UTC)

    if body.confirm:
        # 第一次确认保持版本 1；再次确认递增，前端可据此判断「配置已变更」。
        if project.generation_config_confirmed_at is not None:
            project.generation_config_version = (project.generation_config_version or 1) + 1
        project.generation_config_confirmed_at = datetime.now(UTC)
        project.generation_config_snapshot = _build_snapshot(
            version=project.generation_config_version,
            image=candidate.image_model,
            video=candidate.video_model,
            audio=candidate.audio_model,
            image_capability=_image_capability(
                candidate.image_model.provider_key or "", candidate.image_model.model_name or ""
            ),
            video_capability=_video_capability(
                candidate.video_model.provider_key or "", candidate.video_model.model_name or ""
            ),
            audio_capability=_audio_capability(
                candidate.audio_model.provider_key or "", candidate.audio_model.model_name or ""
            ),
            output=candidate.output,
            policy=candidate.policy,
        )

    return await get_project_generation_config(db, project=project)


async def resolve_project_model(
    db: AsyncSession,
    *,
    project_id: str | None,
    category: ModelCategoryKey,
) -> Model | None:
    """运行期模型解析：项目显式配置优先，缺失才回落全局默认。

    返回 None 表示两边都没配；调用方决定是 503 还是允许可选。
    项目显式配置指向不存在的模型时**不回退**，避免静默换模型。
    """
    project = await db.get(Project, project_id) if project_id else None
    if project is not None:
        explicit = _project_model_id(project, category)
        if explicit:
            model = await db.get(Model, explicit)
            if model is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"项目配置的模型不存在：{explicit}",
                )
            if model.category != category.value:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"项目配置的模型类别不匹配：{explicit}",
                )
            return model

    settings = await db.get(ModelSettings, 1)
    model_id = _settings_model_id(settings, category)
    if not model_id:
        return None
    model = await db.get(Model, model_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"全局默认模型不存在：{model_id}",
        )
    if model.category != category.value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"全局默认模型类别不匹配：{model_id}",
        )
    return model


async def resolve_project_id_for_shot(db: AsyncSession, *, shot_id: str) -> str | None:
    """通过镜头反查项目，供生成链路选择项目模型。"""
    from app.models.studio import Chapter, Shot

    row = await db.execute(
        select(Chapter.project_id)
        .join(Shot, Shot.chapter_id == Chapter.id)
        .where(Shot.id == shot_id)
        .limit(1)
    )
    value = row.scalar_one_or_none()
    return str(value) if value else None


async def resolve_project_id_for_image_relation(
    db: AsyncSession,
    *,
    relation_type: str,
    relation_entity_id: str,
) -> str | None:
    """把图片任务关联实体反查到项目；无法唯一确定时返回 None。

    可唯一反查的场景：
    - `character_image`：角色图 → Character.project_id；
    - `shot_frame_image`：分镜帧 → Shot → Chapter.project_id。
    全局资产（演员/场景/道具/服装）可能被多个项目引用，无法唯一确定，
    此时回退全局默认模型，避免把 A 项目的模型错误用到 B 项目。
    """
    from app.models.studio import (
        Chapter,
        Character,
        CharacterImage,
        Shot,
        ShotFrameImage,
    )

    if relation_type == "character_image":
        try:
            image = await db.get(CharacterImage, int(relation_entity_id))
        except (TypeError, ValueError):
            return None
        if image is None:
            return None
        character = await db.get(Character, image.character_id)
        return character.project_id if character else None

    if relation_type == "shot_frame_image":
        try:
            image = await db.get(ShotFrameImage, int(relation_entity_id))
        except (TypeError, ValueError):
            return None
        if image is None:
            return None
        row = await db.execute(
            select(Chapter.project_id)
            .join(Shot, Shot.chapter_id == Chapter.id)
            .where(Shot.id == image.shot_detail_id)
            .limit(1)
        )
        value = row.scalar_one_or_none()
        return str(value) if value else None

    return None
