"""P2 / C4：项目视觉风格选择、锁定与快照。

锁定约束必须在服务端保证：
- 选择风格：已有快照 → 409/400，不允许改；
- 锁定风格：已有快照 → 拒绝重复锁定；
- 快照保存 prompt_pack、参考图、样张与结构化描述的完整副本，
  之后编辑或删除全局目录项不会影响已锁定项目。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chains.prompts.style_pack import style_pack_line
from app.models.studio import FileItem, Project, ProjectStyleOption, ProjectStyleSnapshot
from app.models.types import FileType
from app.schemas.studio.project_style import (
    ProjectStyleSnapshotRead,
    ProjectStyleStateRead,
)
from app.schemas.studio.projects import ProjectStyleOptionRead
from app.services.studio.style_catalog import list_style_options


async def _get_snapshot(db: AsyncSession, project_id: str) -> ProjectStyleSnapshot | None:
    return await db.get(ProjectStyleSnapshot, project_id)


def _snapshot_read(snapshot: ProjectStyleSnapshot | None) -> ProjectStyleSnapshotRead | None:
    if snapshot is None:
        return None
    return ProjectStyleSnapshotRead.model_validate(snapshot)


async def _validate_image_files(db: AsyncSession, file_ids: list[str], *, label: str) -> list[str]:
    """校验文件存在且是图片；去重后最多 3 张。"""
    unique = [item.strip() for item in file_ids if item and item.strip()]
    unique = list(dict.fromkeys(unique))
    if len(unique) > 3:
        raise ValueError(f"{label}最多 3 张")
    for file_id in unique:
        item = await db.get(FileItem, file_id)
        if item is None:
            raise ValueError(f"{label}文件不存在：{file_id}")
        if item.type != FileType.image:
            raise ValueError(f"{label}必须是图片：{file_id}")
    return unique


async def _find_current_style(
    db: AsyncSession, project: Project
) -> ProjectStyleOption | None:
    row = await db.scalar(
        select(ProjectStyleOption)
        .where(
            ProjectStyleOption.name == project.style,
            ProjectStyleOption.visual_style == project.visual_style,
        )
        .limit(1)
    )
    return row if isinstance(row, ProjectStyleOption) else None


async def get_project_style_state(
    db: AsyncSession, *, project: Project
) -> ProjectStyleStateRead:
    """读取项目风格状态：锁定快照优先，未锁定时返回当前目录选择。"""
    snapshot = await _get_snapshot(db, project.id)
    styles = await list_style_options(db)

    current: ProjectStyleOption | None = None
    if snapshot is not None:
        if snapshot.source_style_id:
            current = await db.get(ProjectStyleOption, snapshot.source_style_id)
    else:
        current = await _find_current_style(db, project)

    visual_styles = list(dict.fromkeys(row.visual_style for row in styles))
    return ProjectStyleStateRead(
        project_id=project.id,
        locked=snapshot is not None,
        style=ProjectStyleOptionRead.model_validate(current) if current else None,
        snapshot=_snapshot_read(snapshot),
        styles=[ProjectStyleOptionRead.model_validate(row) for row in styles],
        visual_styles=visual_styles,
    )


async def select_project_style(
    db: AsyncSession, *, project: Project, style_id: str
) -> ProjectStyleStateRead:
    """未锁定项目选择风格（草稿）；不写快照。"""
    if await _get_snapshot(db, project.id) is not None:
        raise ValueError("项目视觉风格已锁定，不能直接切换；如需更换风格请复制为新项目")

    style = await db.get(ProjectStyleOption, style_id)
    if style is None:
        raise ValueError(f"风格不存在：{style_id}")

    project.style = style.name
    project.visual_style = style.visual_style
    await db.flush()
    return await get_project_style_state(db, project=project)


async def lock_project_style(
    db: AsyncSession,
    *,
    project: Project,
    style_id: str | None = None,
    sample_file_ids: list[str] | None = None,
) -> ProjectStyleStateRead:
    """锁定项目视觉风格并生成快照。

    `style_id` 为空时使用项目当前选择；找不到当前风格则报错。
    样张可以是本次上传的，也可以沿用风格目录里已保存的。
    """
    if await _get_snapshot(db, project.id) is not None:
        raise ValueError("项目视觉风格已锁定，不能重复锁定")

    style: ProjectStyleOption | None = None
    if style_id:
        style = await db.get(ProjectStyleOption, style_id)
    else:
        style = await _find_current_style(db, project)
    if style is None:
        raise ValueError("请先选择一个视觉风格，再执行锁定")

    selected_samples = (
        await _validate_image_files(db, sample_file_ids or [], label="确认样张")
        if sample_file_ids
        else list(style.sample_file_ids or [])
    )
    reference_ids = list(style.reference_file_ids or [])
    # 参考图在创建/更新目录项时已做数量校验；锁定时再确认文件仍然存在。
    reference_ids = await _validate_image_files(db, reference_ids, label="风格参考图")

    effective_prompt = (style.prompt_pack or "").strip() or style_pack_line(
        visual_style=style.visual_style,
        style=style.name,
    )

    snapshot = ProjectStyleSnapshot(
        project_id=project.id,
        source_style_id=style.id,
        style_name=style.name,
        visual_style=style.visual_style,
        description=style.description or "",
        structured_profile=style.structured_profile,
        prompt_pack=effective_prompt,
        reference_file_ids=reference_ids,
        sample_file_ids=selected_samples,
        snapshot_version=1,
        locked_at=datetime.now(UTC),
    )
    db.add(snapshot)

    # 保持旧字段同步：历史页面仍读取 project.style / visual_style。
    project.style = style.name
    project.visual_style = style.visual_style
    if selected_samples:
        style.sample_file_ids = selected_samples

    await db.flush()
    await db.refresh(snapshot)
    return await get_project_style_state(db, project=project)
