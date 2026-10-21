"""人物画像缺失信息分析：结构化输出 schema。"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict


class CharacterPortraitAnalysisResult(BaseModel):
    """根据原文人物描述，分析缺少的信息，并给出优化后的可生成画像描述。"""

    model_config = ConfigDict(extra="forbid")

    issues: List[str]
    optimized_description: str


__all__ = ["CharacterPortraitAnalysisResult"]

