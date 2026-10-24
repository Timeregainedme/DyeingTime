"""P5：AI 分镜规划输出 Schema。

AI 只输出结构化候选；资产 ID、版本 ID、正式 Shot 写入由服务端完成。

P10-C2 收紧点：
- 场次序号、标题、画面描述、视频 Prompt、动作节拍改为必填；
  缺字段必须让本次输出失败并进入受控修复，而不是静默落成“镜头 1 / 空描述”。
- 对白增加 line_mode 与 source_dialogue_index：短信/屏幕文字不得伪装成口语。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlannedDialogue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = Field(..., min_length=1)
    speaker_name: str | None = None
    emotion: str = ""
    # DIALOGUE=人物口语；NARRATION=旁白；SCREEN_TEXT=短信/字幕/屏幕文字；
    # ACTION=仅用于后期拟音的动作提示，不应交给 TTS。
    line_mode: Literal["DIALOGUE", "NARRATION", "SCREEN_TEXT", "ACTION"] = "DIALOGUE"
    # 对应输入“已确认对白”的 1-based 序号；口语对白必须填写以便追溯。
    source_dialogue_index: int | None = Field(None, ge=1)


class PlannedShot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    order: int = Field(..., ge=1)
    scene_group_index: int = Field(..., ge=1, description="对应输入场次列表的 1-based 序号")
    title: str = Field(..., min_length=1, max_length=120)
    script_excerpt: str = ""
    source_quote: str = ""
    duration_seconds: int = Field(5, ge=1, le=60)
    camera_shot: str = "MS"
    angle: str = "EYE_LEVEL"
    movement: str = "STATIC"
    action_beats: list[str] = Field(..., min_length=1)
    atmosphere: str = ""
    visual_description: str = Field(..., min_length=10)
    video_prompt_draft: str = Field(..., min_length=10)
    character_names: list[str] = Field(default_factory=list)
    scene_name: str | None = None
    prop_names: list[str] = Field(default_factory=list)
    costume_name: str | None = None
    dialogues: list[PlannedDialogue] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_source(self) -> "PlannedShot":
        if not (self.script_excerpt or "").strip() and not (self.source_quote or "").strip():
            raise ValueError("script_excerpt 与 source_quote 至少填写一个")
        return self


class ShotPlanResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shots: list[PlannedShot] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)
    notes: str = ""


__all__ = ["PlannedDialogue", "PlannedShot", "ShotPlanResult"]
