"""任务所属工作区的解析。

为什么需要这个模块：
`generation_tasks.workspace_id` 是 NOT NULL，但任务的创建入口分散在
    - `app/services/script_processing_tasks.py`（6 处）
    - `app/services/studio/image_task_runner.py`
    - `app/services/studio/audio_task_runner.py`
    - `app/services/film/generated_video.py`
    - `app/api/v1/routes/film/generated_video.py`、`tasks_images.py`
这些入口的业务入参各不相同（chapter_id / project_id / shot_id / 多态 relation_entity_id），
但任务归属总能由它已关联的业务实体唯一确定。集中在这里回溯，调用方无需感知租户概念。

为什么不兜底到默认工作区：
兜底会把无法判定归属的任务放进 `ws-default`，等于对默认租户泄露。
宁可抛错让创建失败 —— 调用方必须传一个真实存在的业务实体。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import (
    ActorImage,
    Chapter,
    Character,
    CharacterImage,
    CostumeImage,
    Project,
    PropImage,
    SceneImage,
    Shot,
)


async def _from_project(db: AsyncSession, project_id: str | None) -> str | None:
    if not project_id:
        return None
    return await db.scalar(select(Project.workspace_id).where(Project.id == project_id))


async def _from_chapter(db: AsyncSession, chapter_id: str | None) -> str | None:
    if not chapter_id:
        return None
    return await db.scalar(
        select(Project.workspace_id)
        .join(Chapter, Chapter.project_id == Project.id)
        .where(Chapter.id == chapter_id)
    )


async def _from_shot(db: AsyncSession, shot_id: str | None) -> str | None:
    if not shot_id:
        return None
    return await db.scalar(
        select(Project.workspace_id)
        .join(Chapter, Chapter.project_id == Project.id)
        .join(Shot, Shot.chapter_id == Chapter.id)
        .where(Shot.id == shot_id)
    )


async def _from_asset_image(
    db: AsyncSession,
    *,
    relation_type: str,
    relation_entity_id: str | None,
) -> str | None:
    """从「资产图片行」回溯工作区。

    资产图任务的 `relation_entity_id` 是**图片行的主键**（如 costume_images.id），
    不是 project/chapter/shot，因此上面那三个解释器永远查不到——
    这正是「1 个服装未生成：无法确定任务所属工作区」的根因。

    这里按图片行找到所属资产，再由资产回溯项目：
    - 角色：characters.project_id（项目内实体）
    - 演员/场景/道具/服装：项目关联表里第一条（这些实体是全局的，项目归属由关联决定）
    """
    # 延迟导入：file_usages 会经 app.services.studio.__init__ 反向依赖本模块，
    # 放在模块顶部会形成循环导入（API 直接起不来）。
    from app.services.studio.file_usages import (
        first_project_id_for_actor,
        first_project_id_for_costume,
        first_project_id_for_prop,
        first_project_id_for_scene,
    )

    if not relation_type or not relation_entity_id:
        return None

    # 角色直接用字符串主键，不需要走「图片行 ID」这一步（图片行 ID 是整数）
    if relation_type == "character":
        character = await db.get(Character, relation_entity_id)
        return await _from_project(db, character.project_id if character else None)

    try:
        image_pk = int(relation_entity_id)
    except (TypeError, ValueError):
        return None

    if relation_type == "actor_image":
        row = await db.get(ActorImage, image_pk)
        project_id = await first_project_id_for_actor(db, row.actor_id) if row else None
    elif relation_type == "scene_image":
        row = await db.get(SceneImage, image_pk)
        project_id = await first_project_id_for_scene(db, row.scene_id) if row else None
    elif relation_type == "prop_image":
        row = await db.get(PropImage, image_pk)
        project_id = await first_project_id_for_prop(db, row.prop_id) if row else None
    elif relation_type == "costume_image":
        row = await db.get(CostumeImage, image_pk)
        project_id = await first_project_id_for_costume(db, row.costume_id) if row else None
    elif relation_type == "character_image":
        row = await db.get(CharacterImage, image_pk)
        character = await db.get(Character, row.character_id) if row else None
        project_id = character.project_id if character else None
    else:
        return None

    return await _from_project(db, project_id)


async def resolve_workspace_id(
    db: AsyncSession,
    *,
    project_id: str | None = None,
    chapter_id: str | None = None,
    shot_id: str | None = None,
    relation_entity_id: str | None = None,
    relation_type: str | None = None,
) -> str:
    """解析任务所属工作区。

    参数：
    - `project_id` / `chapter_id` / `shot_id`：已知的业务实体 ID；
    - `relation_entity_id`：多态的关联实体 ID；`relation_type` 为资产图类型
      （`actor_image` / `scene_image` / `prop_image` / `costume_image` /
      `character_image` / `character`）时按图片行或角色回溯项目；
    - 其余情况按「项目 → 章节 → 镜头」顺序探测。

    返回：
    - 命中的 `workspace_id`。

    失败语义：
    - 所有解释都查不到 → ValueError；
    - 多个解释指向不同工作区 → ValueError（说明数据被跨租户错误关联）。

    两者都会由 `app/main.py` 的 ValueError handler 转成 400，不会变成 500。
    """
    candidates: list[str] = []
    for resolved in (
        await _from_project(db, project_id),
        await _from_chapter(db, chapter_id),
        await _from_shot(db, shot_id),
        await _from_asset_image(
            db, relation_type=relation_type or "", relation_entity_id=relation_entity_id
        ),
        await _from_project(db, relation_entity_id),
        await _from_chapter(db, relation_entity_id),
        await _from_shot(db, relation_entity_id),
    ):
        if resolved:
            candidates.append(resolved)

    if not candidates:
        raise ValueError("无法确定任务所属工作区：关联的业务实体不存在")

    unique = set(candidates)
    if len(unique) > 1:
        raise ValueError("任务关联的业务实体分属不同工作区，拒绝创建")

    return candidates[0]
