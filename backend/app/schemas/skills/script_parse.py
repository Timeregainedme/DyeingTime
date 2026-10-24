"""P3 / C6：AI 剧本结构化解析的 Pydantic Schema。

AI 输出只是候选，不等于已确认事实。字段保持 name-based（不生成业务 ID），
已有实体匹配由服务端/人工审核完成。
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DialogueMode = Literal[
    "DIALOGUE",
    "VOICE_OVER",
    "OFF_SCREEN",
    "PHONE",
    "NARRATION",
    "SCREEN_TEXT",
    "ACTION",
]


class ParseEvidence(BaseModel):
    """原文证据：chunk + 字符区间 + 摘录，用于审核页定位。"""

    model_config = ConfigDict(extra="ignore")

    chunk_id: str = ""
    start_char: int | None = None
    end_char: int | None = None
    quote: str = ""


class ParsedCharacter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    aliases: list[str] = Field(default_factory=list)
    role: str = ""
    age_range: str = ""
    appearance: str = ""
    hairstyle: str = ""
    body_type: str = ""
    base_costume: str = ""
    voice_description: str = ""
    episodes: list[int] = Field(default_factory=list)
    matched_character_id: str | None = None

    @field_validator("episodes", mode="before")
    @classmethod
    def _coerce_episodes(cls, value: Any) -> list[int]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        result: list[int] = []
        for item in value:
            if isinstance(item, int):
                result.append(item)
            elif isinstance(item, str):
                match = re.search(r"\d+", item)
                if match:
                    result.append(int(match.group()))
        return result
    evidence: list[ParseEvidence] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class ParsedScene(BaseModel):
    """场景资产候选（不是 P5 的场次 SceneGroup）。"""

    model_config = ConfigDict(extra="ignore")

    name: str
    location_type: str = ""
    interior_exterior: str = ""
    spatial_features: str = ""
    time_light: str = ""
    key_furnishings: str = ""
    is_existing: bool = False
    matched_scene_id: str | None = None
    evidence: list[ParseEvidence] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class ParsedProp(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    appearance: str = ""
    color_material: str = ""
    story_usage: str = ""
    holder_character: str = ""
    location: str = ""
    is_existing: bool = False
    matched_prop_id: str | None = None
    evidence: list[ParseEvidence] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class ParsedCostumeChange(BaseModel):
    model_config = ConfigDict(extra="ignore")

    character_name: str
    base_costume: str = ""
    changed_costume: str = ""
    story_position: str = ""
    reason: str = ""
    applicable_episode: int | None = None
    suggested_scene: str = ""
    evidence: list[ParseEvidence] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class ParsedSceneBeat(BaseModel):
    """剧情场次建议；P3 只保存候选，不创建正式 SceneGroup。"""

    model_config = ConfigDict(extra="ignore")

    index: int = 1
    title: str = ""
    location: str = ""
    time_of_day: str = ""
    characters: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    source_range: str = ""
    evidence: list[ParseEvidence] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class ParsedEpisode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = ""
    summary: str = ""
    major_events: list[str] = Field(default_factory=list)
    scene_beats: list[ParsedSceneBeat] = Field(default_factory=list)


class ParsedDialogue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    speaker_name: str | None = None
    order: int = 0
    emotion: str = ""
    line_mode: DialogueMode = "DIALOGUE"
    story_range: str = ""

    @field_validator("line_mode", mode="before")
    @classmethod
    def _coerce_line_mode(cls, value: Any) -> str:
        """把模型常见的同义写法归一到受控枚举，避免整份解析因一个词失败。"""
        raw = str(value or "DIALOGUE").strip().upper()
        mapping = {
            "SMS": "SCREEN_TEXT",
            "MESSAGE": "SCREEN_TEXT",
            "TEXT": "SCREEN_TEXT",
            "SUBTITLE": "SCREEN_TEXT",
            "ON_SCREEN": "SCREEN_TEXT",
            "NARRATOR": "NARRATION",
            "VOICE_OVER": "VOICE_OVER",
            "OFF_SCREEN": "OFF_SCREEN",
            "PHONE": "PHONE",
            "ACTION": "ACTION",
        }
        return mapping.get(raw, raw if raw in {
            "DIALOGUE", "VOICE_OVER", "OFF_SCREEN", "PHONE", "NARRATION", "SCREEN_TEXT", "ACTION"
        } else "DIALOGUE")
    speaker_unresolved: bool = False
    evidence: list[ParseEvidence] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class ParsedIssue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str = "other"
    message: str
    related: str = ""
    evidence: list[ParseEvidence] = Field(default_factory=list)


class ScriptParseResult(BaseModel):
    """一次性解析的完整候选结果。"""

    model_config = ConfigDict(extra="ignore")

    characters: list[ParsedCharacter] = Field(default_factory=list)
    scenes: list[ParsedScene] = Field(default_factory=list)
    props: list[ParsedProp] = Field(default_factory=list)
    costume_changes: list[ParsedCostumeChange] = Field(default_factory=list)
    episode: ParsedEpisode = Field(default_factory=ParsedEpisode)
    dialogues: list[ParsedDialogue] = Field(default_factory=list)
    issues: list[ParsedIssue] = Field(default_factory=list)
    notes: str = ""


__all__ = [
    "ParsedCharacter",
    "ParsedCostumeChange",
    "ParsedDialogue",
    "ParsedEpisode",
    "ParsedIssue",
    "ParsedProp",
    "ParsedScene",
    "ParsedSceneBeat",
    "ScriptParseResult",
]
