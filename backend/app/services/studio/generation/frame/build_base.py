from __future__ import annotations

from pydantic import Field

from app.models.studio import ShotFrameType
from app.services.studio.generation.shared.types import GenerationBaseDraft


class FrameBaseDraft(GenerationBaseDraft):
    """分镜帧图片生成的基础提示词真值。"""

    kind: str = "frame"
    shot_id: str
    frame_type: ShotFrameType
    prompt: str
    director_command_summary: str = ""
    continuity_guidance: str = ""
    frame_specific_guidance: str = ""
    composition_anchor: str = ""
    screen_direction_guidance: str = ""
    # 最终渲染阶段统一追加的约束；为空时由渲染层使用代码内置默认值。
    negative_prompt: str = ""
    avoid_items: list[str] = Field(default_factory=list)
    style_pack: str = ""


def build_frame_base_draft(
    *,
    shot_id: str,
    frame_type: ShotFrameType,
    prompt: str,
    director_command_summary: str = "",
    continuity_guidance: str = "",
    frame_specific_guidance: str = "",
    composition_anchor: str = "",
    screen_direction_guidance: str = "",
    negative_prompt: str = "",
    avoid_items: list[str] | None = None,
    style_pack: str = "",
) -> FrameBaseDraft:
    """构造分镜帧基础草稿，并附带最终渲染阶段仍需保留的高优先级约束。"""
    return FrameBaseDraft(
        shot_id=shot_id,
        frame_type=frame_type,
        prompt=(prompt or "").strip(),
        director_command_summary=(director_command_summary or "").strip(),
        continuity_guidance=(continuity_guidance or "").strip(),
        frame_specific_guidance=(frame_specific_guidance or "").strip(),
        composition_anchor=(composition_anchor or "").strip(),
        screen_direction_guidance=(screen_direction_guidance or "").strip(),
        negative_prompt=(negative_prompt or "").strip(),
        avoid_items=[str(item).strip() for item in (avoid_items or []) if str(item).strip()],
        style_pack=(style_pack or "").strip(),
    )
