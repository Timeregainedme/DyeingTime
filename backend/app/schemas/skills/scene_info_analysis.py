"""场景信息缺失分析：结构化输出 schema。"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict


class SceneInfoAnalysisResult(BaseModel):
    """根据原文场景描述，分析缺少的信息，并给出优化后的可生成场景描述。"""

    model_config = ConfigDict(extra="forbid")

    issues: List[str]
    optimized_description: str


__all__ = ["SceneInfoAnalysisResult"]

