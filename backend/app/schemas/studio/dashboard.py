"""创作工作台的只读聚合 schemas。

为什么单独建一个 schema 模块：
工作台首页需要「项目 + 章节 + 镜头 + 任务 + 待审核」的统一快照。
如果让前端逐个项目、逐个章节地拉取，会退化成 N+1 请求，也无法保证
多个数字来自同一时刻。这里用一个响应把首页需要的真实数据一次带出。

注意：阶段状态机（待录入原文 / 待提取分镜 / …）仍由前端
`getChapterPreparationState` 唯一计算；后端只提供判断所需的原始字段，
避免同一规则在前后端各写一份后逐渐漂移。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DashboardStatsRead(BaseModel):
    """顶部四个统计卡片。口径见各字段说明，全部按当前工作区过滤。"""

    project_count: int = Field(..., description="当前工作区项目总数")
    pending_review_shots: int = Field(
        ..., description="存在已成功生成视频、但该视频任务尚未人工审核的镜头数"
    )
    running_tasks: int = Field(
        ..., description="当前工作区处于 pending/running/streaming 的任务数"
    )
    adopted_videos: int = Field(
        ..., description="已采纳视频（shots.generated_video_file_id 非空）的镜头数"
    )


class DashboardChapterRead(BaseModel):
    """章节准备态判断所需的最小字段集合。"""

    id: str
    index: int
    title: str
    has_raw_text: bool
    storyboard_count: int
    status: str


class DashboardProjectRead(BaseModel):
    """项目卡片 + 「继续创作」所需的项目级快照。"""

    id: str
    name: str
    description: str
    style: str
    visual_style: str
    updated_at: datetime | None = None

    chapter_count: int
    chapters: list[DashboardChapterRead] = Field(default_factory=list)

    total_shots: int
    pending_shots: int
    ready_shots: int
    pending_review_shots: int
    adopted_videos: int
    running_tasks: int


class DashboardTaskRead(BaseModel):
    """最近生成任务概览。只暴露任务中心已有的通用字段。"""

    id: str
    task_kind: str
    status: str
    progress: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    project_id: str | None = None
    project_name: str | None = None


class DashboardReviewRead(BaseModel):
    """待审核事项。

    `kind` 决定前端跳转位置：
    - shot_extraction → 剧集镜头准备
    - shot_plan → 分镜规划审核
    - video_candidate → 视频候选审核
    """

    kind: Literal["shot_extraction", "shot_plan", "video_candidate"]
    label: str
    count: int
    project_id: str | None = None
    project_name: str | None = None
    chapter_id: str | None = None


class DashboardRead(BaseModel):
    """创作工作台首页的一次性快照。"""

    # 仅用于前端隐藏无权执行的按钮；真正的门禁仍在各写接口的 require_editor。
    can_edit: bool = Field(..., description="当前工作区角色是否具备编辑权限（viewer 为 false）")
    stats: DashboardStatsRead
    projects: list[DashboardProjectRead] = Field(default_factory=list)
    recent_tasks: list[DashboardTaskRead] = Field(default_factory=list)
    pending_reviews: list[DashboardReviewRead] = Field(default_factory=list)


__all__ = [
    "DashboardStatsRead",
    "DashboardChapterRead",
    "DashboardProjectRead",
    "DashboardTaskRead",
    "DashboardReviewRead",
    "DashboardRead",
]
