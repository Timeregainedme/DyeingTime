"""P5：正式场次（SceneGroup）schemas。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SceneGroupBase(BaseModel):
    chapter_id: str
    index: int = Field(..., ge=1)
    title: str = ""
    description: str = ""
    location: str = ""
    time_of_day: str = ""
    story_event: str = ""
    primary_scene_id: str | None = None


class SceneGroupCreate(BaseModel):
    title: str = ""
    description: str = ""
    location: str = ""
    time_of_day: str = ""
    story_event: str = ""
    primary_scene_id: str | None = None
    index: int | None = Field(None, ge=1, description="不传则追加到末尾")


class SceneGroupUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    time_of_day: str | None = None
    story_event: str | None = None
    primary_scene_id: str | None = None
    index: int | None = Field(None, ge=1)


class SceneGroupRead(SceneGroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    primary_scene_name: str | None = None
    primary_scene_thumbnail: str = ""
    shot_count: int = 0
    total_duration: int = 0
    source_parse_run_id: str | None = None
    source_beat_key: str | None = None
    source_start_char: int | None = None
    source_end_char: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SceneGroupReorderRequest(BaseModel):
    group_ids: list[str] = Field(..., min_length=1)


class ShotOrderItem(BaseModel):
    shot_id: str
    scene_group_id: str | None = None


class ShotReorderRequest(BaseModel):
    """按给定顺序重写章节内 index；未列出的镜头追加到末尾。"""

    items: list[ShotOrderItem] = Field(..., min_length=1)


class SceneBeatSuggestion(BaseModel):
    beat_key: str
    index: int
    title: str = ""
    description: str = ""
    location: str = ""
    time_of_day: str = ""
    story_event: str = ""
    primary_scene_id: str | None = None
    primary_scene_name: str = ""
    source_start_char: int | None = None
    source_end_char: int | None = None
    already_imported: bool = False
    evidence: list[dict] = Field(default_factory=list)


class SceneGroupSuggestionRead(BaseModel):
    chapter_id: str
    parse_run_id: str | None = None
    source_script_version_id: str | None = None
    current_active_version_id: str | None = None
    script_version_changed: bool = False
    existing_group_count: int = 0
    items: list[SceneBeatSuggestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SceneGroupImportItem(BaseModel):
    beat_key: str | None = None
    title: str = ""
    description: str = ""
    location: str = ""
    time_of_day: str = ""
    story_event: str = ""
    primary_scene_id: str | None = None
    source_start_char: int | None = None
    source_end_char: int | None = None


class SceneGroupImportRequest(BaseModel):
    parse_run_id: str | None = None
    items: list[SceneGroupImportItem] | None = None
    skip_existing: bool = True


class SceneGroupImportRead(BaseModel):
    created: list[SceneGroupRead] = Field(default_factory=list)
    skipped: int = 0
    warnings: list[str] = Field(default_factory=list)
