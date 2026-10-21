from __future__ import annotations

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
    )
