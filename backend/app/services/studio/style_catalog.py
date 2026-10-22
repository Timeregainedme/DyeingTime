"""风格目录服务。

风格从「枚举」改为「表」的原因见 `ProjectStyleOption` 的文档：
业务上会持续出现新题材/新画风，用枚举意味着每加一个风格都要改代码发版。

这里只做三件事：
1. 列出目录（按画面表现形式分组、组内按 sort_order）；
2. 增删改（名称在同组内唯一）；
3. 首次访问时用内置枚举做种子，保证升级后行为与原来一致。
"""

from __future__ import annotations

import uuid
from collections import OrderedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chains.prompts.style_pack import STYLE_PACKS
from app.models.studio import ProjectStyle, ProjectStyleOption, ProjectStyleSnapshot, ProjectVisualStyle
from app.services.common import entity_not_found

# 内置风格的中文说明，用于首次种子；用户后续可自行修改。
_BUILTIN_DESCRIPTIONS: dict[str, str] = {
    "真人都市": "现代都市实拍，冷暖对比、窗光与霓虹混合",
    "真人科幻": "近未来实拍，冷蓝青基调与体积光",
    "真人古装": "古装实拍，暖黄烛光与丝绸质感",
    "动漫科幻": "科幻动画，高饱和撞色与发光边缘",
    "动漫3D": "三维渲染动画，柔和全局光照",
    "国漫": "国风动画，低饱和与笔锋线条",
    "水墨画": "水墨渲染，宣纸质地与留白",
}


def _builtin_options() -> list[ProjectStyleOption]:
    """按枚举生成内置种子（保持 UI 原有顺序）。"""
    rows: list[ProjectStyleOption] = []
    for index, item in enumerate(ProjectStyle):
        visual = (
            ProjectVisualStyle.live_action
            if item.name.startswith("real_people_")
            else ProjectVisualStyle.anime
        )
        rows.append(
            ProjectStyleOption(
                id=f"style-{uuid.uuid4().hex[:12]}",
                visual_style=visual.value,
                name=item.value,
                description=_BUILTIN_DESCRIPTIONS.get(item.value, ""),
                # 内置风格沿用原有质感描述，保证升级后出图效果不变
                prompt_pack=STYLE_PACKS.get(item.value, ""),
                sort_order=index,
            )
        )
    return rows


async def ensure_style_catalog(db: AsyncSession) -> None:
    """补齐内置风格，同时避免覆盖用户改动。

    - 目录为空：写入历史上全部 7 个内置风格；
    - 目录只有迁移预置的模板（is_builtin=True）：补齐缺失的历史风格，
      保证「新库」与「升级库」最终目录一致；
    - 只要存在任意用户自建风格或已删除过历史风格（存在非 builtin 行），
      就不再自动回填，避免把用户删掉的风格又加回来。
    """
    existing = await db.scalar(select(ProjectStyleOption).limit(1))
    if existing is None:
        db.add_all(_builtin_options())
        await db.flush()
        return

    rows = list((await db.execute(select(ProjectStyleOption))).scalars().all())
    if any(not getattr(row, "is_builtin", False) for row in rows):
        return

    existing_keys = {(row.visual_style, row.name) for row in rows}
    missing = [
        row
        for row in _builtin_options()
        if (row.visual_style, row.name) not in existing_keys
    ]
    if missing:
        db.add_all(missing)
        await db.flush()


async def list_style_options(db: AsyncSession) -> list[ProjectStyleOption]:
    """列出全部风格：先按表现形式分组顺序，再按组内 sort_order。"""
    await ensure_style_catalog(db)
    result = await db.execute(
        select(ProjectStyleOption).order_by(
            ProjectStyleOption.visual_style.asc(),
            ProjectStyleOption.sort_order.asc(),
            ProjectStyleOption.name.asc(),
        )
    )
    rows = list(result.scalars().all())

    # 表现形式按「现实 → 动漫 → 其它」排序，避免字母序把常用项排到后面
    order = {ProjectVisualStyle.live_action.value: 0, ProjectVisualStyle.anime.value: 1}
    rows.sort(key=lambda r: (order.get(r.visual_style, 9), r.sort_order, r.name))
    return rows


def group_style_options(rows: list[ProjectStyleOption]) -> "OrderedDict[str, list[ProjectStyleOption]]":
    """按画面表现形式分组，保持传入顺序。"""
    grouped: OrderedDict[str, list[ProjectStyleOption]] = OrderedDict()
    for row in rows:
        grouped.setdefault(row.visual_style, []).append(row)
    return grouped


async def get_style_option(db: AsyncSession, style_id: str) -> ProjectStyleOption:
    row = await db.get(ProjectStyleOption, style_id)
    if row is None:
        raise ValueError(entity_not_found("ProjectStyle"))
    return row


async def create_style_option(
    db: AsyncSession,
    *,
    visual_style: str,
    name: str,
    description: str = "",
    prompt_pack: str = "",
    sort_order: int | None = None,
    structured_profile: dict[str, object] | None = None,
    reference_file_ids: list[str] | None = None,
    sample_file_ids: list[str] | None = None,
    analysis_status: str = "draft",
) -> ProjectStyleOption:
    """新增风格。

    校验两件事：表现形式非空、同组内名称不重复。
    重名会让项目创建时的「风格 + 表现形式」组合产生歧义，必须挡住。
    """
    visual = (visual_style or "").strip()
    style_name = (name or "").strip()
    if not visual:
        raise ValueError("请选择画面表现形式")
    if not style_name:
        raise ValueError("请填写风格名称")

    await ensure_style_catalog(db)
    duplicated = await db.scalar(
        select(ProjectStyleOption).where(
            ProjectStyleOption.visual_style == visual,
            ProjectStyleOption.name == style_name,
        )
    )
    if duplicated is not None:
        raise ValueError(f"「{visual}」下已存在风格「{style_name}」")

    if sort_order is None:
        # 默认排到该组末尾
        max_order = await db.scalar(
            select(ProjectStyleOption.sort_order)
            .where(ProjectStyleOption.visual_style == visual)
            .order_by(ProjectStyleOption.sort_order.desc())
            .limit(1)
        )
        sort_order = int(max_order or 0) + 1

    row = ProjectStyleOption(
        id=f"style-{uuid.uuid4().hex[:12]}",
        visual_style=visual,
        name=style_name,
        description=(description or "").strip(),
        prompt_pack=(prompt_pack or "").strip()
        or build_prompt_pack_from_profile(structured_profile),
        sort_order=sort_order,
        structured_profile=structured_profile,
        reference_file_ids=_normalize_file_ids(reference_file_ids, label="风格参考图"),
        sample_file_ids=_normalize_file_ids(sample_file_ids, label="确认样张"),
        analysis_status=_normalize_analysis_status(analysis_status),
        is_builtin=False,
    )
    db.add(row)
    await db.flush()
    return row


async def update_style_option(
    db: AsyncSession,
    *,
    style_id: str,
    name: str | None = None,
    description: str | None = None,
    prompt_pack: str | None = None,
    sort_order: int | None = None,
    structured_profile: dict[str, object] | None = None,
    reference_file_ids: list[str] | None = None,
    sample_file_ids: list[str] | None = None,
    analysis_status: str | None = None,
) -> ProjectStyleOption:
    row = await get_style_option(db, style_id)

    if name is not None:
        next_name = name.strip()
        if not next_name:
            raise ValueError("风格名称不能为空")
        if next_name != row.name:
            duplicated = await db.scalar(
                select(ProjectStyleOption).where(
                    ProjectStyleOption.visual_style == row.visual_style,
                    ProjectStyleOption.name == next_name,
                    ProjectStyleOption.id != row.id,
                )
            )
            if duplicated is not None:
                raise ValueError(f"「{row.visual_style}」下已存在风格「{next_name}」")
            row.name = next_name

    if description is not None:
        row.description = description.strip()
    if structured_profile is not None:
        row.structured_profile = structured_profile
    if prompt_pack is not None:
        # 空串表示「让后端按结构化字段生成」，而不是把已有描述清空。
        row.prompt_pack = prompt_pack.strip() or build_prompt_pack_from_profile(
            structured_profile if structured_profile is not None else row.structured_profile
        )
    elif structured_profile is not None:
        # 只改结构化描述时同步生成 prompt pack，避免两者长期不一致。
        row.prompt_pack = build_prompt_pack_from_profile(structured_profile)
    if reference_file_ids is not None:
        row.reference_file_ids = _normalize_file_ids(reference_file_ids, label="风格参考图")
    if sample_file_ids is not None:
        row.sample_file_ids = _normalize_file_ids(sample_file_ids, label="确认样张")
    if analysis_status is not None:
        row.analysis_status = _normalize_analysis_status(analysis_status)
    if sort_order is not None:
        row.sort_order = sort_order

    await db.flush()
    return row


async def delete_style_option(db: AsyncSession, *, style_id: str) -> None:
    """删除风格。

    不阻止「已被项目使用」的删除：历史项目里的 style 是字符串，删掉目录项不会破坏数据，
    只是新建项目时不再出现。若需要强约束，后续可在这里加一次引用计数检查。
    """
    row = await get_style_option(db, style_id)
    await db.delete(row)
    await db.flush()


_PROFILE_LABELS: tuple[tuple[str, str], ...] = (
    ("medium", "视觉媒介"),
    ("texture", "画面质感"),
    ("color", "色彩"),
    ("lighting", "光照"),
    ("material", "材质"),
    ("character_rendering", "人物渲染"),
    ("scene_rendering", "场景渲染"),
    ("camera", "镜头语言"),
    ("keep", "保持"),
)


def build_prompt_pack_from_profile(profile: dict[str, object] | None) -> str:
    """把结构化字段拼成一段可直接注入提示词的质感描述。

    风格描述不是越长为好：只保留有内容的字段，用逗号分隔；
    `avoid` 单独成句，避免和正向描述混在一起被模型误读。
    """
    if not profile:
        return ""
    parts: list[str] = []
    for key, label in _PROFILE_LABELS:
        value = str(profile.get(key) or "").strip()
        if value:
            parts.append(f"{label}：{value}")
    avoid = str(profile.get("avoid") or "").strip()
    if avoid:
        parts.append(f"避免：{avoid}")
    return "；".join(parts)


def _normalize_file_ids(values: list[str] | None, *, label: str) -> list[str]:
    """文件 ID 去重、去空；最多 3 张（参考图与样张同一上限）。"""
    normalized = [str(item).strip() for item in (values or []) if str(item).strip()]
    unique = list(dict.fromkeys(normalized))
    if len(unique) > 3:
        raise ValueError(f"{label}最多 3 张")
    return unique


def _normalize_analysis_status(value: str | None) -> str:
    status = (value or "draft").strip() or "draft"
    if status not in {"draft", "analyzed"}:
        raise ValueError("analysis_status 只支持 draft / analyzed")
    return status


async def resolve_style_motif(
    db: AsyncSession,
    *,
    style: str,
    project_id: str | None = None,
) -> str | None:
    """取出风格提示词质感描述。

    P2 起优先读项目锁定快照：锁定后即使编辑/删除全局目录项，
    已锁定项目的生成提示词也保持不变。未锁定时再查目录。
    返回 None 表示「目录里没配」，调用方会回落到内置 `STYLE_PACKS`。
    """
    if project_id:
        snapshot = await db.get(ProjectStyleSnapshot, project_id)
        if isinstance(snapshot, ProjectStyleSnapshot):
            text = (snapshot.prompt_pack or "").strip()
            if text:
                return text

    name = (style or "").strip()
    if not name:
        return None

    row = await db.scalar(
        select(ProjectStyleOption).where(ProjectStyleOption.name == name).limit(1)
    )
    # scalar 在极少数情况下可能返回非行对象（自定义驱动/测试替身会返回计数），
    # 这里只接受真正的目录行，其余一律当作「没配置」，避免属性访问炸穿生成链路。
    if not isinstance(row, ProjectStyleOption):
        return None
    text = (row.prompt_pack or "").strip()
    return text or None
