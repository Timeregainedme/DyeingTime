"""Project/Chapter 的请求响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.studio import ChapterStatus, ProjectVisualStyle


PROJECT_STYLE_EXAMPLES = ["真人都市", "真人电影写实", "2D 动画", "3D 国漫"]


class ProjectBase(BaseModel):
    name: str = Field(..., description="项目名称")
    description: str = Field("", description="项目简介")
    style: str = Field(..., description="题材/风格（来自项目风格目录）", examples=PROJECT_STYLE_EXAMPLES)
    visual_style: ProjectVisualStyle = Field(ProjectVisualStyle.live_action, description="画面表现形式")
    seed: int = Field(0, description="随机种子")
    unify_style: bool = Field(True, description="是否统一风格")
    progress: int = Field(0, description="进度百分比（0-100）")
    default_video_ratio: str | None = Field(None, description="项目级默认视频比例；分镜未覆盖时生效")
    default_image_ratio: str | None = Field(None, description="项目级默认图片比例；为空时回落到视频比例")
    default_image_resolution_profile: str | None = Field(
        None, description="项目级默认图片分辨率档位（standard/high）；为空时回落到提供方默认档位"
    )
    default_video_resolution: str | None = Field(
        None, description="项目级默认视频分辨率档位（如 768p/2k）；为空时回落到提供方默认档位"
    )
    use_dialog_audio_as_reference: bool = Field(
        False,
        description=(
            "视频生成时是否自动带上镜头台词已生成的配音作为参考音频"
            "（true=使用，false=纯画面参考）；新项目默认关闭"
        ),
    )
    stats: dict[str, Any] = Field(default_factory=dict, description="聚合统计（JSON）")


class ProjectCreate(ProjectBase):
    id: str = Field(..., description="项目 ID")


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    style: str | None = Field(None, description="题材/风格（来自项目风格目录）", examples=PROJECT_STYLE_EXAMPLES)
    visual_style: ProjectVisualStyle | None = None
    seed: int | None = None
    unify_style: bool | None = None
    progress: int | None = None
    default_video_ratio: str | None = None
    default_image_ratio: str | None = None
    default_image_resolution_profile: str | None = None
    default_video_resolution: str | None = None
    use_dialog_audio_as_reference: bool | None = None
    stats: dict[str, Any] | None = None


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    # 多租户归属对外可见：前端切换工作区、展示「谁建的」都依赖这两个字段。
    # 只读——不接受通过 ProjectUpdate 修改，避免客户端把自己项目搬进别的租户。
    workspace_id: str = Field(..., description="所属工作区 ID")
    created_by: int | None = Field(None, description="创建者账号 ID")

    # --- P2：项目生成配置 ---
    # 全部只读；写入走 `PUT /studio/projects/{id}/generation-config`，避免
    # 通过通用 PATCH 绕过能力校验与确认逻辑。
    default_image_model_id: str | None = Field(None, description="项目默认图片模型 ID")
    default_video_model_id: str | None = Field(None, description="项目默认视频模型 ID")
    default_audio_model_id: str | None = Field(None, description="项目默认音频模型 ID")
    default_reference_mode: str | None = Field(None, description="默认参考模式")
    default_shot_duration: int | None = Field(None, description="默认镜头时长（秒）")
    video_duration_min: int | None = Field(None, description="项目业务时长下限（秒）")
    video_duration_max: int | None = Field(None, description="项目业务时长上限（秒）")
    video_concurrency: int | None = Field(None, description="视频批量并发数")
    generation_config_version: int | None = Field(None, description="生成配置版本")
    generation_config_confirmed_at: datetime | None = Field(
        None, description="生成配置确认时间；为空表示未确认"
    )
    generation_config_updated_at: datetime | None = Field(
        None, description="生成配置最近保存时间"
    )


class ChapterBase(BaseModel):
    project_id: str = Field(..., description="所属项目 ID")
    index: int = Field(..., description="章节序号（项目内唯一）")
    title: str = Field(..., description="章节标题")
    summary: str = Field("", description="章节摘要")
    raw_text: str = Field("", description="章节原文")
    condensed_text: str = Field("", description="精简原文")
    storyboard_count: int = Field(0, description="分镜数量")
    status: ChapterStatus = Field(ChapterStatus.draft, description="章节状态")


class ChapterCreate(ChapterBase):
    id: str = Field(..., description="章节 ID")


class ChapterUpdate(BaseModel):
    project_id: str | None = None
    index: int | None = None
    title: str | None = None
    summary: str | None = None
    raw_text: str | None = None
    condensed_text: str | None = None
    storyboard_count: int | None = None
    status: ChapterStatus | None = None


class ChapterRead(ChapterBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shot_count: int = Field(0, description="分镜数（shots 条数聚合）")


class StyleOption(BaseModel):
    """通用下拉选项。"""

    value: str = Field(..., description="选项值")
    label: str = Field(..., description="选项展示文案")


class ProjectStyleOptionsRead(BaseModel):
    """项目风格候选项。"""

    visual_styles: list[StyleOption] = Field(default_factory=list, description="视觉风格可选项")
    styles_by_visual_style: dict[str, list[StyleOption]] = Field(
        default_factory=dict,
        description="按视觉风格分组的视频风格选项",
    )
    default_style_by_visual_style: dict[str, str] = Field(
        default_factory=dict,
        description="各视觉风格默认视频风格",
    )


class ProjectProductionReadinessCheck(BaseModel):
    """开工预检单项结果。"""

    key: str = Field(..., description="检查项标识")
    label: str = Field("", description="检查项名称")
    ok: bool = Field(..., description="该项是否通过")
    message: str = Field("", description="结果说明；未通过时给出可执行的修复指引")
    detail: dict[str, Any] = Field(default_factory=dict, description="该项补充数据")


class ProjectProductionReadinessRead(BaseModel):
    """项目开工预检报告（只读聚合，不修改任何状态）。"""

    project_id: str = Field(..., description="项目 ID")
    ready: bool = Field(..., description="是否全部通过，可以开工")
    checks: list[ProjectProductionReadinessCheck] = Field(default_factory=list, description="检查项明细")
    stats: dict[str, Any] = Field(default_factory=dict, description="项目当前规模统计")


class CharacterRecurrenceRead(BaseModel):
    """单个角色的跨集出现情况。

    存在的意义：角色要不要绑定演员取决于它出现在几集里 —— 跨集反复出现的必须绑，
    只在一集内出现的不需要（用户口径 m09145）。把章节数直接给前端，编辑角色时就能标出来。
    """

    character_id: str = Field(..., description="角色 ID")
    chapter_count: int = Field(..., description="该角色出现的去重章节（集）数")
    recurring: bool = Field(..., description="是否为跨集反复出现的主角级角色（需要绑定演员）")


class ProjectCharacterRecurrenceRead(BaseModel):
    """项目下全部角色的跨集出现情况（只读）。"""

    project_id: str = Field(..., description="项目 ID")
    min_chapters: int = Field(..., description="判定为主角级所需的最少章节数")
    items: list[CharacterRecurrenceRead] = Field(default_factory=list, description="角色明细")


class StyleStructuredProfile(BaseModel):
    """风格的结构化描述；AI 分析输出与人工修订共用同一形状。"""

    medium: str = Field("", description="视觉媒介")
    texture: str = Field("", description="画面质感")
    color: str = Field("", description="色彩与饱和度")
    lighting: str = Field("", description="光照方式")
    material: str = Field("", description="材质特征")
    character_rendering: str = Field("", description="人物渲染特征")
    scene_rendering: str = Field("", description="场景渲染特征")
    camera: str = Field("", description="摄影与运镜风格")
    keep: str = Field("", description="应当保持的视觉特征")
    avoid: str = Field("", description="禁止出现的风格特征")


class ProjectStyleOptionRead(BaseModel):
    """风格目录项。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    visual_style: str = Field(..., description="所属画面表现形式（现实/动漫…）")
    name: str = Field(..., description="风格名称")
    description: str = Field("", description="面向用户的说明")
    prompt_pack: str = Field("", description="提示词质感描述（注入到出图提示词）")
    sort_order: int = Field(0, description="同组内排序")
    structured_profile: StyleStructuredProfile | None = Field(
        None, description="AI 分析/人工修订的结构化风格字段"
    )
    reference_file_ids: list[str] = Field(default_factory=list, description="风格参考图文件 ID")
    sample_file_ids: list[str] = Field(default_factory=list, description="已确认样张文件 ID")
    analysis_status: str = Field("draft", description="AI 分析状态：draft / analyzed")
    is_builtin: bool = Field(False, description="是否平台内置模板")

    @field_validator("reference_file_ids", "sample_file_ids", mode="before")
    @classmethod
    def _none_to_empty_list(cls, value: object) -> object:
        """迁移后的老行为 NULL；对外统一为空列表，前端不必判空。"""
        return value or []


class ProjectStyleOptionCreate(BaseModel):
    """新增风格。"""

    visual_style: str = Field(..., description="所属画面表现形式")
    name: str = Field(..., description="风格名称")
    description: str = Field("", description="面向用户的说明")
    prompt_pack: str = Field("", description="提示词质感描述；留空则用内置风格包")
    sort_order: int | None = Field(None, description="同组内排序；不传则排到末尾")
    structured_profile: StyleStructuredProfile | None = Field(
        None, description="结构化风格字段"
    )
    reference_file_ids: list[str] = Field(default_factory=list, description="风格参考图（1–3 张）")
    sample_file_ids: list[str] = Field(default_factory=list, description="确认样张（0–3 张）")
    analysis_status: str = Field("draft", description="draft / analyzed")


class ProjectStyleOptionUpdate(BaseModel):
    """修改风格（只改传入的字段）。"""

    name: str | None = None
    description: str | None = None
    prompt_pack: str | None = None
    sort_order: int | None = None
    structured_profile: StyleStructuredProfile | None = None
    reference_file_ids: list[str] | None = None
    sample_file_ids: list[str] | None = None
    analysis_status: str | None = None
