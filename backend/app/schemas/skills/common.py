"""影视/脚本处理链路的通用结构与枚举映射。"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Common ----------
DialogueLineMode = Literal["DIALOGUE", "VOICE_OVER", "OFF_SCREEN", "PHONE"]


class EvidenceSpan(BaseModel):
    """可追溯证据：原文定位（chunk + 起止位置/摘录），用于审核与回查。"""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(..., description="输入文本块的唯一ID（例如 chapter1_p03）")
    start_char: Optional[int] = Field(None, description="在该 chunk 中的起始字符位置（可选）")
    end_char: Optional[int] = Field(None, description="在该 chunk 中的结束字符位置（可选）")
    quote: Optional[str] = Field(None, description="不超过200字的原文摘录（可选，便于人工审核）")


class DialogueLine(BaseModel):
    """单条对白：说话人/对象、正文、情绪与表达方式、旁白/电话等模式、镜头内时间点。"""

    model_config = ConfigDict(extra="forbid")

    index: Optional[int] = Field(
        None,
        ge=0,
        description="可选：镜头内排序（脚本处理链路用于保持原始顺序）",
    )
    speaker_character_id: Optional[str] = Field(None, description="说话人角色ID，若无法判定可为空")
    target_character_id: Optional[str] = Field(None, description="对谁说（听者角色ID），可选")
    text: str = Field(..., description="对白正文")
    emotion: Optional[str] = Field(None, description="情绪/语气（如：愤怒、平静、哽咽）")
    delivery: Optional[str] = Field(None, description="表达方式（如：低声、喊叫、旁白腔）")
    line_mode: DialogueLineMode = Field(
        "DIALOGUE",
        description="DIALOGUE=正常对白, VOICE_OVER=旁白, OFF_SCREEN=画外音, PHONE=电话音等",
    )
    start_time_sec: Optional[float] = Field(None, ge=0, description="在该镜头内相对起始时间（秒），用于对口型/字幕切分")
    evidence: List[EvidenceSpan] = Field(default_factory=list, description="原文依据")


# ---------- Story / Scenes ----------
SceneTime = Literal["DAY", "NIGHT", "DAWN", "DUSK", "UNKNOWN"]
SceneInterior = Literal["INT", "EXT", "INT_EXT", "UNKNOWN"]


# ---------- Cinematic (Shots / Transitions / VFX) ----------
ShotType = Literal["ECU", "CU", "MCU", "MS", "MLS", "LS", "ELS"]
CameraAngle = Literal["EYE_LEVEL", "HIGH_ANGLE", "LOW_ANGLE", "BIRD_EYE", "DUTCH", "OVER_SHOULDER"]
CameraMovement = Literal[
    "STATIC",
    "PAN",
    "TILT",
    "DOLLY_IN",
    "DOLLY_OUT",
    "TRACK",
    "CRANE",
    "HANDHELD",
    "STEADICAM",
    "ZOOM_IN",
    "ZOOM_OUT",
]
TransitionType = Literal["CUT", "DISSOLVE", "WIPE", "FADE_IN", "FADE_OUT", "MATCH_CUT", "J_CUT", "L_CUT"]
VFXType = Literal[
    "NONE",
    "PARTICLES",
    "VOLUMETRIC_FOG",
    "CG_DOUBLE",
    "DIGITAL_ENVIRONMENT",
    "MATTE_PAINTING",
    "FIRE_SMOKE",
    "WATER_SIM",
    "DESTRUCTION",
    "ENERGY_MAGIC",
    "COMPOSITING_CLEANUP",
    "SLOW_MOTION_TIME",
    "OTHER",
]
ComplexityLevel = Literal["LOW", "MEDIUM", "HIGH"]


# ---------- 英文枚举 → 中文映射（影视/分镜专业用语） ----------
DIALOGUE_LINE_MODE_ZH: dict[str, str] = {
    "DIALOGUE": "对白",
    "VOICE_OVER": "旁白",
    "OFF_SCREEN": "画外音",
    "PHONE": "电话声",
}

SCENE_TIME_ZH: dict[str, str] = {
    "DAY": "日",
    "NIGHT": "夜",
    "DAWN": "黎明",
    "DUSK": "黄昏",
    "UNKNOWN": "未知",
}

SCENE_INTERIOR_ZH: dict[str, str] = {
    "INT": "内景",
    "EXT": "外景",
    "INT_EXT": "内景兼外景",
    "UNKNOWN": "未知",
}

SHOT_TYPE_ZH: dict[str, str] = {
    "ECU": "大特写",
    "CU": "特写",
    "MCU": "中近景",
    "MS": "中景",
    "MLS": "中远景",
    "LS": "远景",
    "ELS": "大远景",
}

CAMERA_ANGLE_ZH: dict[str, str] = {
    "EYE_LEVEL": "平视",
    "HIGH_ANGLE": "俯拍",
    "LOW_ANGLE": "仰拍",
    "BIRD_EYE": "鸟瞰",
    "DUTCH": "荷兰角",
    "OVER_SHOULDER": "过肩",
}

CAMERA_MOVEMENT_ZH: dict[str, str] = {
    "STATIC": "固定",
    "PAN": "横摇",
    "TILT": "俯仰",
    "DOLLY_IN": "推轨",
    "DOLLY_OUT": "拉轨",
    "TRACK": "跟拍",
    "CRANE": "升降",
    "HANDHELD": "手持",
    "STEADICAM": "斯坦尼康",
    "ZOOM_IN": "变焦推进",
    "ZOOM_OUT": "变焦拉远",
}

TRANSITION_TYPE_ZH: dict[str, str] = {
    "CUT": "切",
    "DISSOLVE": "叠化",
    "WIPE": "划变",
    "FADE_IN": "淡入",
    "FADE_OUT": "淡出",
    "MATCH_CUT": "匹配剪辑",
    "J_CUT": "J 剪",
    "L_CUT": "L 剪",
}

VFX_TYPE_ZH: dict[str, str] = {
    "NONE": "无",
    "PARTICLES": "粒子",
    "VOLUMETRIC_FOG": "体积雾",
    "CG_DOUBLE": "数字替身",
    "DIGITAL_ENVIRONMENT": "数字场景",
    "MATTE_PAINTING": "绘景",
    "FIRE_SMOKE": "烟火",
    "WATER_SIM": "水效",
    "DESTRUCTION": "破碎/解算",
    "ENERGY_MAGIC": "能量/魔法",
    "COMPOSITING_CLEANUP": "合成/修脏",
    "SLOW_MOTION_TIME": "升格/慢动作",
    "OTHER": "其他",
}

COMPLEXITY_ZH: dict[str, str] = {
    "LOW": "低",
    "MEDIUM": "中",
    "HIGH": "高",
}

PROP_CATEGORY_ZH: dict[str, str] = {
    "weapon": "武器",
    "document": "文书/证件",
    "vehicle": "载具",
    "clothing": "服装",
    "device": "器械/设备",
    "magic_item": "魔法/特殊物品",
    "other": "其他",
}


class VFXNote(BaseModel):
    """单条视效说明：类型、描述、复杂度及原文依据。"""

    model_config = ConfigDict(extra="forbid")

    vfx_type: VFXType = "NONE"
    description: Optional[str] = Field(None, description="视效说明（简短、可执行）")
    complexity: Optional[ComplexityLevel] = Field(None, description="粗略复杂度")
    evidence: List[EvidenceSpan] = Field(default_factory=list, description="原文依据（若为忠实抽取）")


class Transition(BaseModel):
    """镜头间转场：从哪镜到哪镜、转场类型及可选说明。"""

    model_config = ConfigDict(extra="forbid")

    from_shot_id: str
    to_shot_id: str
    transition: TransitionType = "CUT"
    note: Optional[str] = Field(None, description="为何用该转场（可选）")


class Uncertainty(BaseModel):
    """结构化不确定项：字段路径、原因及可选证据，便于人工审核与回溯。"""

    model_config = ConfigDict(extra="forbid")

    field_path: str = Field(..., description="如 characters[0].name、scenes[2].location_id")
    reason: str = Field(..., description="不确定原因简述")
    evidence: List[EvidenceSpan] = Field(default_factory=list, description="相关原文依据（可选）")


__all__ = [
    "DialogueLineMode",
    "EvidenceSpan",
    "DialogueLine",
    "SceneTime",
    "SceneInterior",
    "ShotType",
    "CameraAngle",
    "CameraMovement",
    "TransitionType",
    "VFXType",
    "ComplexityLevel",
    "DIALOGUE_LINE_MODE_ZH",
    "SCENE_TIME_ZH",
    "SCENE_INTERIOR_ZH",
    "SHOT_TYPE_ZH",
    "CAMERA_ANGLE_ZH",
    "CAMERA_MOVEMENT_ZH",
    "TRANSITION_TYPE_ZH",
    "VFX_TYPE_ZH",
    "COMPLEXITY_ZH",
    "PROP_CATEGORY_ZH",
    "VFXNote",
    "Transition",
    "Uncertainty",
]

