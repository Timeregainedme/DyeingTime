from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerationBaseDraft(BaseModel):
    """生成准备中的基础真值。"""

    kind: str = Field(..., description="生成类型，如 frame / video / asset_image")


class GenerationContext(BaseModel):
    """本次生成使用的动态上下文。"""

    kind: str = Field(..., description="生成类型，如 frame / video / asset_image")


class GenerationDerivedPreview(BaseModel):
    """基于基础真值与上下文推导出的预览结果。"""

    kind: str = Field(..., description="生成类型，如 frame / video / asset_image")
    warnings: list[str] = Field(default_factory=list, description="推导阶段产生的轻量告警")
    quality_checks: dict[str, Any] | None = Field(default=None, description="质量校验结果")
    debug_context: dict[str, Any] | None = Field(default=None, description="调试上下文")


class GenerationSubmissionPayload(BaseModel):
    """真正提交给模型的最终载荷。"""

    kind: str = Field(..., description="生成类型，如 frame / video / asset_image")
    prompt: str = Field(..., description="最终提交给模型的提示词")
    images: list[str] = Field(default_factory=list, description="按顺序提交的参考图 file_id")
    extra: dict[str, Any] = Field(default_factory=dict, description="额外提交上下文")

