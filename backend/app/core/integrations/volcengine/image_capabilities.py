"""火山图片能力声明与覆盖注册。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.integrations.image_capabilities import ImageModelCapability

if TYPE_CHECKING:
    from app.core.contracts.image_generation import ImageGenerationInput

_VOLCENGINE_RATIO_SIZE_PROFILES = {
    "1:1": {"standard": "2048x2048", "high": "3072x3072"},
    "4:3": {"standard": "2304x1728", "high": "3456x2592"},
    "3:4": {"standard": "1728x2304", "high": "2592x3456"},
    "16:9": {"standard": "2848x1600", "high": "4096x2304"},
    "9:16": {"standard": "1600x2848", "high": "2304x4096"},
    "3:2": {"standard": "2496x1664", "high": "3744x2496"},
    "2:3": {"standard": "1664x2496", "high": "2496x3744"},
    "21:9": {"standard": "3136x1344", "high": "4704x2016"},
}

_VOLCENGINE_DEFAULT = ImageModelCapability(
    supports_seed=True,
    supports_watermark=True,
    allowed_sizes={
        size
        for profiles in _VOLCENGINE_RATIO_SIZE_PROFILES.values()
        for size in profiles.values()
    },
    supported_ratios=set(_VOLCENGINE_RATIO_SIZE_PROFILES.keys()),
    default_resolution_profile="standard",
    ratio_size_profiles=_VOLCENGINE_RATIO_SIZE_PROFILES,
)

# key: 模型前缀（小写）
_VOLCENGINE_MODEL_OVERRIDES: dict[str, ImageModelCapability] = {}


def register_volcengine_image_capability(*, model_prefix: str, capability: ImageModelCapability) -> None:
    prefix = model_prefix.strip().lower()
    if not prefix:
        raise ValueError("model_prefix must not be empty")
    _VOLCENGINE_MODEL_OVERRIDES[prefix] = capability


def clear_volcengine_image_capability_overrides() -> None:
    _VOLCENGINE_MODEL_OVERRIDES.clear()


def _pick_override(model: str | None) -> ImageModelCapability | None:
    if not model:
        return None
    value = model.strip().lower()
    if not value:
        return None
    for prefix, cap in sorted(_VOLCENGINE_MODEL_OVERRIDES.items(), key=lambda item: len(item[0]), reverse=True):
        if value.startswith(prefix):
            return cap
    return None


def resolve_volcengine_image_capability(model: str | None) -> ImageModelCapability:
    return _pick_override(model) or _VOLCENGINE_DEFAULT


def validate_volcengine_image_options(input_: ImageGenerationInput) -> None:
    """火山能力校验入口（避免调用侧传 provider 字面量）。"""
    from app.core.contracts.image_generation import ImageGenerationInput
    from app.core.integrations.image_capabilities import validate_image_options

    assert isinstance(input_, ImageGenerationInput)
    validate_image_options(provider="volcengine", model=input_.model, input_=input_)
