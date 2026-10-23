"""P5：AI 分镜规划输出 Schema。

AI 只输出结构化候选；资产 ID、版本 ID、正式 Shot 写入由服务端完成。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlannedDialogue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    speaker_name: str | None = None
    emotion: str = ""
    line_mode: str = "DIALOGUE"


class PlannedShot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order: int = 1
    scene_group_index: int = Field(1, ge=1, description="对应输入场次列表的 1-based 序号")
    title: str = ""
    script_excerpt: str = ""
    source_quote: str = ""
    duration_seconds: int = 5
    camera_shot: str = "MS"
    angle: str = "EYE_LEVEL"
    movement: str = "STATIC"
    action_beats: list[str] = Field(default_factory=list)
    atmosphere: str = ""
    visual_description: str = ""
    video_prompt_draft: str = ""
    character_names: list[str] = Field(default_factory=list)
    scene_name: str | None = None
    prop_names: list[str] = Field(default_factory=list)
    costume_name: str | None = None
    dialogues: list[PlannedDialogue] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class ShotPlanResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shots: list[PlannedShot] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)
    notes: str = ""


__all__ = ["PlannedDialogue", "PlannedShot", "ShotPlanResult"]
