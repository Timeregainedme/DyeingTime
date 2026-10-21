from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ShotFramePromptInput(BaseModel):
    """镜头帧提示词生成输入，与 Shot + ShotDetail 字段对齐。"""

    model_config = ConfigDict(extra="forbid")

    script_excerpt: str = Field(..., description="剧本摘录，对应 Shot.script_excerpt")
    title: str = Field("", description="镜头标题，对应 Shot.title")
    visual_style: Optional[str] = Field(None, description="画面表现形式（现实/动漫等）")
    style: Optional[str] = Field(None, description="题材/风格")
    unify_style: Optional[bool] = Field(None, description="是否要求镜头间统一继承项目风格")
    camera_shot: Optional[str] = Field(None, description="景别，如 ECU/CU/MS")
    angle: Optional[str] = Field(None, description="机位角度")
    movement: Optional[str] = Field(None, description="运镜方式")
    atmosphere: Optional[str] = Field(None, description="氛围描述")
    shot_description: Optional[str] = Field(None, description="镜头整体描述或补充说明")
    mood_tags: Optional[List[str]] = Field(None, description="情绪标签")
    vfx_type: Optional[str] = Field(None, description="视效类型")
    vfx_note: Optional[str] = Field(None, description="视效说明")
    duration: Optional[int] = Field(None, description="时长（秒）")
    scene_id: Optional[str] = Field(None, description="关联场景 ID")
    dialog_summary: Optional[str] = Field(None, description="对白摘要")
    action_beats: Optional[List[str]] = Field(None, description="按时间顺序排列的动作拍点")
    action_beat_phases: Optional[str] = Field(None, description="动作拍点的阶段摘要，如 trigger / peak / aftermath")
    selected_action_beat_phase: Optional[str] = Field(None, description="当前帧优先消费的动作阶段")
    selected_action_beat_text: Optional[str] = Field(None, description="当前帧优先消费的动作拍点原文")
    character_context: Optional[str] = Field(None, description="镜头已确认角色及描述")
    scene_context: Optional[str] = Field(None, description="镜头已确认场景及描述")
    prop_context: Optional[str] = Field(None, description="镜头已确认道具及描述")
    costume_context: Optional[str] = Field(None, description="镜头已确认服装及描述")
    subject_priority: Optional[str] = Field(None, description="主体优先级建议，说明本镜头应优先写谁、先写哪个场景")
    previous_shot_title: Optional[str] = Field(None, description="上一镜头标题，用于连续性承接")
    previous_shot_script_excerpt: Optional[str] = Field(None, description="上一镜头剧本摘录，用于连续性承接")
    previous_shot_end_state: Optional[str] = Field(None, description="上一镜头结尾状态摘要")
    next_shot_title: Optional[str] = Field(None, description="下一镜头标题，用于连续性承接")
    next_shot_script_excerpt: Optional[str] = Field(None, description="下一镜头剧本摘录，用于连续性承接")
    next_shot_start_goal: Optional[str] = Field(None, description="下一镜头起始目标摘要")
    continuity_guidance: Optional[str] = Field(None, description="当前镜头与相邻镜头的承接建议")
    composition_anchor: Optional[str] = Field(None, description="画面构图与空间锚点建议")
    screen_direction_guidance: Optional[str] = Field(None, description="人物朝向、视线与左右轴线建议")
    frame_specific_guidance: Optional[str] = Field(None, description="按首帧/关键帧/尾帧区分的专项生成建议")
    director_command_summary: Optional[str] = Field(None, description="汇总后的导演指令摘要，高优先级约束")
    retry_guidance: Optional[str] = Field(None, description="自动重试时附加的修正要求")


class ShotFramePromptResult(BaseModel):
    """镜头帧提示词生成结果：单个 prompt 字符串。"""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., description="画面描述提示词，可写入 ShotDetail 对应字段")
    debug_context: dict[str, Any] | None = Field(None, description="本次生成使用的上下文，便于排查与调试")


__all__ = ["ShotFramePromptInput", "ShotFramePromptResult"]
