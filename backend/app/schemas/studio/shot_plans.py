"""P5：AI 分镜规划草稿与镜头资产版本 schemas。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Pace = Literal["slow", "standard", "fast"]


class ShotPlanRequest(BaseModel):
    target_duration: int = Field(90, ge=30, le=300, description="目标总时长（秒）")
    pace: Pace = Field("standard", description="镜头节奏：slow/standard/fast")
    force: bool = Field(False, description="已有同来源草稿时是否重新规划")


class PlanCharacterRef(BaseModel):
    character_id: str
    name: str = ""
    identity_version_id: str | None = None
    appearance_version_id: str | None = None


class PlanAssetRef(BaseModel):
    asset_id: str
    name: str = ""
    asset_version_id: str | None = None


class PlanDialogueLine(BaseModel):
    text: str
    speaker_character_id: str | None = None
    speaker_name: str | None = None
    emotion: str = ""
    line_mode: str = "DIALOGUE"


class ShotPlanPayload(BaseModel):
    """正式可编辑的镜头候选 payload。"""

    title: str = ""
    script_excerpt: str = ""
    source_start_char: int | None = None
    source_end_char: int | None = None
    duration: int = 5
    camera_shot: str = "MS"
    angle: str = "EYE_LEVEL"
    movement: str = "STATIC"
    action_beats: list[str] = Field(default_factory=list)
    atmosphere: str = ""
    description: str = ""
    video_prompt: str = ""
    characters: list[PlanCharacterRef] = Field(default_factory=list)
    scene: PlanAssetRef | None = None
    props: list[PlanAssetRef] = Field(default_factory=list)
    costume: PlanAssetRef | None = None
    dialogues: list[PlanDialogueLine] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class ShotPlanCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    draft_id: str
    order_index: int
    scene_group_id: str | None = None
    candidate_key: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    review_status: str = "pending"
    source_key: str | None = None
    created_at: datetime | None = None


class ShotPlanDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    chapter_id: str
    source_parse_run_id: str | None = None
    source_script_version_id: str | None = None
    target_duration: int = 90
    pace: str = "standard"
    status: str = "draft"
    model_id: str | None = None
    model_name: str = ""
    provider_name: str = ""
    prompt_version: str = ""
    prompt_hash: str = ""
    task_id: str | None = None
    error: str = ""
    scene_group_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    coverage: dict[str, Any] = Field(default_factory=dict)
    applied_at: datetime | None = None
    applied_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    candidates: list[ShotPlanCandidateRead] = Field(default_factory=list)


class ShotPlanCandidateUpdate(BaseModel):
    payload: dict[str, Any] | None = None
    order_index: int | None = Field(None, ge=1)
    scene_group_id: str | None = None
    review_status: str | None = None


class ShotPlanCandidateCreate(BaseModel):
    scene_group_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ShotPlanReorderRequest(BaseModel):
    candidate_ids: list[str] = Field(..., min_length=1)


class ShotPlanConfirmRequest(BaseModel):
    append_to_existing: bool = Field(
        False, description="章节已有镜头时必须显式为 true；本阶段只允许追加，不覆盖旧镜头"
    )


class ShotPlanConfirmRead(BaseModel):
    draft: ShotPlanDraftRead
    shot_ids: list[str] = Field(default_factory=list)
    reused: bool = False
    warnings: list[str] = Field(default_factory=list)


class ShotPlanStatsRead(BaseModel):
    chapter_id: str
    latest_draft_id: str | None = None
    status: str | None = None
    target_duration: int | None = None
    shot_count: int = 0
    total_duration: int = 0
    min_duration: int | None = None
    max_duration: int | None = None
    coverage_ratio: float = 0.0
    blocking_issue_count: int = 0
    warning_count: int = 0


class ShotAssetVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shot_id: str
    asset_type: str
    asset_id: str
    asset_version_id: str | None = None
    role: str
    slot: int = 0
    source: str = "plan"
    created_at: datetime | None = None


class ShotPlanMergeRequest(BaseModel):
    source_candidate_id: str
    target_candidate_id: str
