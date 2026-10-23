"""时间线 / 成片导出相关 schema。

说明：
- 时间线是**聚合视图**，不新建表：镜头本身已经是「按章节顺序排列的片段」，
  这里按 `chapter.index` → `shot.index` 排好序并把时长累加成 `start`/`end`。
- `duration` 只认 `ShotDetail.duration`（镜头唯一时长来源），缺失时按 0 处理，
  并在 `stats` 里如实暴露，避免前端把「没配时长」误当成「零长度片段」。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TimelineFrameRead(BaseModel):
    """片段携带的分镜帧（首帧/关键帧/尾帧）。"""

    frame_type: str
    file_id: str | None = None
    width: int | None = None
    height: int | None = None
    format: str = "png"


class TimelineDialogRead(BaseModel):
    """片段里的台词行，带已生成配音的关联文件。"""

    line_id: int
    index: int
    text: str
    emotion: str | None = None
    speaker_name: str | None = None
    audio_file_id: str | None = None


class TimelineClipRead(BaseModel):
    """时间线上的一个片段（= 一个镜头）。"""

    shot_id: str
    chapter_id: str
    chapter_index: int
    chapter_title: str
    scene_group_id: str | None = None
    scene_index: int = 0
    scene_title: str = ""
    index: int
    title: str
    status: str
    duration: int = Field(0, description="秒；取自 ShotDetail.duration，缺失为 0")
    start: float = Field(0, description="在成片中的起始秒")
    end: float = Field(0, description="在成片中的结束秒")
    video_file_id: str | None = Field(None, description="当前采用的视频文件 ID；为空表示还没生成")
    audio_file_id: str | None = Field(None, description="分镜级配音文件 ID")
    thumbnail: str = ""
    frames: list[TimelineFrameRead] = Field(default_factory=list)
    dialogs: list[TimelineDialogRead] = Field(default_factory=list)


class TimelineStatsRead(BaseModel):
    clip_count: int
    total_duration: float
    clips_with_video: int
    clips_missing_video: int
    clips_with_audio: int
    exportable: bool = Field(..., description="全部片段都有视频时才可导出成片")


class ProjectTimelineRead(BaseModel):
    project_id: str
    project_name: str
    video_ratio: str | None = None
    clips: list[TimelineClipRead] = Field(default_factory=list)
    stats: TimelineStatsRead


class TimelineExportRead(BaseModel):
    """导出结果：一个可直接下载的成片文件。"""

    file_id: str
    name: str
    storage_key: str
    download_path: str
    clip_count: int
    duration: float


class ClipsExportSelection(BaseModel):
    """选择式片段导出范围；shot_ids 优先，其次场次、剧集，最后 include_all。"""

    shot_ids: list[str] | None = Field(
        None, description="自定义镜头 ID 列表；按数据库业务顺序重排，不按传入顺序"
    )
    chapter_ids: list[str] | None = Field(None, description="剧集 ID 列表")
    scene_group_ids: list[str] | None = Field(None, description="场次 ID 列表")
    include_all: bool = Field(False, description="选择项目内全部镜头")


class ClipsExportRequest(ClipsExportSelection):
    """正式导出请求；expected_plan_hash 用于防止预检查后采纳版本变化。"""

    expected_plan_hash: str | None = Field(
        None, description="预检查返回的 plan_hash；不一致时拒绝导出"
    )


class ClipsExportItemRead(BaseModel):
    """预检查中的单个镜头导出项。"""

    shot_id: str
    chapter_id: str
    chapter_index: int
    chapter_title: str = ""
    scene_group_id: str | None = None
    scene_index: int = 0
    scene_title: str = ""
    shot_index: int
    title: str = ""
    duration: int = 0
    file_id: str | None = None
    file_name: str
    status: str = Field("ok", description="ok/no_accepted/file_missing/storage_unavailable/unsupported_format")
    size_bytes: int = 0
    error: str = ""


class ClipsExportPrecheckRead(BaseModel):
    """选择式 ZIP 导出的预检查结果。"""

    project_id: str
    project_name: str
    selected_count: int
    exportable_count: int
    no_accepted_count: int
    file_missing_count: int
    unsupported_count: int
    total_duration: float
    estimated_size: int = 0
    plan_hash: str
    can_download: bool
    items: list[ClipsExportItemRead] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
