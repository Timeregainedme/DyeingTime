"""影视抽取/分镜相关的结构化输出模型（API 暴露用）。"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.skills.common import (
    CameraAngle,
    CameraMovement,
    DialogueLine,
    EvidenceSpan,
    SceneInterior,
    SceneTime,
    ShotType,
    Transition,
    Uncertainty,
    VFXNote,
)


# ---------- Entities ----------
class Character(BaseModel):
    """从小说中抽取的角色：主名、别名、外貌与性格、服装描述、首次出场证据及抽取置信度。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="稳定ID，例如 char_001")
    name: str = Field(..., description="主名称（尽量取原文最常用的称呼）")
    normalized_name: Optional[str] = Field(None, description="归一化主名，如将「王二/二哥/王二哥」统一为同一主名（来自文本）")
    aliases: List[str] = Field(default_factory=list, description="别名/称呼（原文出现过的）")
    description: Optional[str] = Field(None, description="外貌/身份/气质（忠实原文，与服装区分）")
    costume_note: Optional[str] = Field(
        None,
        description="从原文抽取的服装/造型描述（如款式、颜色、配饰），与 description 区分，便于后续关联服装资产",
    )
    traits: List[str] = Field(default_factory=list, description="性格/特征词（尽量来自原文）")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="抽取确定度 0-1（模型输出）")
    first_appearance: Optional[EvidenceSpan] = None


class Location(BaseModel):
    """从小说中抽取的地点：名称、类型、场景描写及首次出场证据、置信度。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="稳定ID，例如 loc_001")
    name: str = Field(..., description="地点名称（原文）")
    normalized_name: Optional[str] = Field(None, description="归一化名称（来自文本）")
    type: Optional[str] = Field(None, description="地点类型：房间/街道/森林/车厢等（可选）")
    description: Optional[str] = Field(None, description="场景描写（忠实原文，简短）")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="抽取确定度 0-1（模型输出）")
    first_appearance: Optional[EvidenceSpan] = None


class Prop(BaseModel):
    """从小说中抽取的道具：名称、类别、外观/用途、归属角色及首次出场证据、置信度。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="稳定ID，例如 prop_001")
    name: str = Field(..., description="道具名称（原文）")
    normalized_name: Optional[str] = Field(None, description="归一化名称（来自文本）")
    category: Optional[str] = Field(None, description="可选：weapon/document/vehicle/clothing/device/magic_item/other")
    description: Optional[str] = Field(None, description="外观/用途（忠实原文）")
    owner_character_id: Optional[str] = Field(None, description="拥有者（如果明确）")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="抽取确定度 0-1（模型输出）")
    first_appearance: Optional[EvidenceSpan] = None


# ---------- Story / Scenes ----------
class Scene(BaseModel):
    """场景：内/外景、时间、关联地点与人物/道具，含原文标题与系统格式化标题。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="例如 scene_001")
    raw_title: Optional[str] = Field(None, description="来自原文的场景标题（若存在）")
    formatted_title: Optional[str] = Field(None, description="系统生成的影视格式标题，如 INT. 地点 - TIME")
    interior: SceneInterior = "UNKNOWN"
    time_of_day: SceneTime = "UNKNOWN"

    location_id: Optional[str] = Field(None, description="loc_xxx，如可判定")
    summary: Optional[str] = Field(None, description="场景发生了什么（忠实原文，短）")

    character_ids: List[str] = Field(default_factory=list, description="该场景出现的人物ID")
    prop_ids: List[str] = Field(default_factory=list, description="该场景关键道具ID")
    evidence: List[EvidenceSpan] = Field(default_factory=list, description="支持该场景的证据片段（可多条）")


class Shot(BaseModel):
    """单镜头：景别/机位/运镜、时长与画面描述、对白列表、音效与视效、关联角色与道具。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="例如 shot_001_003（scene_001 第3镜）")
    scene_id: str = Field(..., description="所属 scene_xxx")
    order: int = Field(..., ge=1, description="场景内镜头序号，从1开始")

    shot_type: ShotType
    camera_angle: CameraAngle = "EYE_LEVEL"
    camera_movement: CameraMovement = "STATIC"

    # 可拍性/执行信息
    duration_sec: Optional[float] = Field(None, ge=0.5, le=30, description="建议时长（可选）")
    description: str = Field(..., description="镜头里发生的动作/画面（行业口吻，简短可拍）")

    character_ids: List[str] = Field(default_factory=list)
    prop_ids: List[str] = Field(default_factory=list)

    vfx: List[VFXNote] = Field(default_factory=list)
    sfx: List[str] = Field(default_factory=list, description="音效提示，如 footsteps, rain, explosion（可选）")
    dialogue_lines: List[DialogueLine] = Field(
        default_factory=list,
        description="该镜头内的对白列表（结构化：说话人、对象、情绪、旁白/电话等、时间点）",
    )
    dialogue: Optional[str] = Field(None, description="[兼容] 若该镜头承载关键对白，可摘录/概述（可选）")

    evidence: List[EvidenceSpan] = Field(default_factory=list, description="对应原文依据（可选）")


class ProjectCinematicBreakdown(BaseModel):
    """从小说抽取的完整影视分镜：元信息、实体表、场景表、镜头表、转场表及不确定项。"""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(..., description="小说/章节标识，例如 novel_x_ch05")
    source_title: Optional[str] = Field(None, description="书名/章节名（从书名页或章节头抽取）")
    source_author: Optional[str] = Field(None, description="作者（若可从文本抽取）")
    language: Optional[str] = Field(None, description="如 zh、en，便于后续提示词与分词")
    extraction_version: Optional[str] = Field(None, description="本次抽取器版本，便于回溯差异")
    schema_version: Optional[str] = Field(None, description="本输出使用的 schema 版本")

    chunks: List[str] = Field(default_factory=list, description="本次处理的 chunk_id 列表")

    characters: List[Character] = Field(default_factory=list)
    locations: List[Location] = Field(default_factory=list)
    props: List[Prop] = Field(default_factory=list)

    scenes: List[Scene] = Field(default_factory=list)
    shots: List[Shot] = Field(default_factory=list)
    transitions: List[Transition] = Field(default_factory=list)

    notes: List[str] = Field(default_factory=list, description="全局备注/不确定点（可选）")
    uncertainties: List[Uncertainty] = Field(
        default_factory=list,
        description="结构化不确定项：field_path、reason、evidence",
    )


# ---------- Skill Results (API-level) ----------
class TextChunk(BaseModel):
    """输入的文本块。chunk_id 会写入 EvidenceSpan.chunk_id 用于回查。"""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(..., description="例如 chapter1_p03 / ch05_para12")
    text: str = Field(..., description="该 chunk 的原文文本")


class FilmEntityExtractionResult(BaseModel):
    """实体抽取结果（复用 Character/Location/Prop/Uncertainty）。"""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(..., description="小说/章节标识，例如 novel_x_ch05")
    language: Optional[str] = Field(None, description="如 zh/en（可选）")
    extraction_version: Optional[str] = Field(None, description="抽取器版本（可选）")
    schema_version: Optional[str] = Field(None, description="schemas 版本（可选）")

    chunks: List[str] = Field(default_factory=list, description="本次处理的 chunk_id 列表")

    characters: List[Character] = Field(default_factory=list)
    locations: List[Location] = Field(default_factory=list)
    props: List[Prop] = Field(default_factory=list)

    notes: List[str] = Field(default_factory=list, description="全局备注（可选）")
    uncertainties: List[Uncertainty] = Field(default_factory=list, description="结构化不确定项")


class FilmShotlistResult(BaseModel):
    """分镜输出（直接复用 ProjectCinematicBreakdown）。"""

    model_config = ConfigDict(extra="forbid")

    breakdown: ProjectCinematicBreakdown = Field(..., description="影视化拆解结果")


__all__ = [
    "Character",
    "Location",
    "Prop",
    "Scene",
    "Shot",
    "ProjectCinematicBreakdown",
    "TextChunk",
    "FilmEntityExtractionResult",
    "FilmShotlistResult",
]

