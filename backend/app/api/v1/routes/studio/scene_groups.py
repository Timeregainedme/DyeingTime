"""P5 / C9：正式场次 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.scoping import get_chapter_in_workspace, get_scene_group_in_workspace
from app.dependencies import WorkspaceContext, get_db, require_editor, require_viewer
from app.schemas.common import ApiResponse, created_response, empty_response, success_response
from app.schemas.studio.scene_groups import (
    SceneGroupCreate,
    SceneGroupImportRead,
    SceneGroupImportRequest,
    SceneGroupRead,
    SceneGroupReorderRequest,
    SceneGroupSuggestionRead,
    SceneGroupUpdate,
    ShotReorderRequest,
)
from app.schemas.studio.shots import ShotRead
from app.services.studio.scene_groups import (
    create_group,
    delete_group,
    get_group,
    get_scene_group_suggestions,
    import_scene_group_suggestions,
    list_group_shots,
    list_groups,
    reorder_chapter_shots,
    reorder_groups,
    update_group,
)

router = APIRouter()


@router.get(
    "/chapters/{chapter_id}/scene-groups",
    response_model=ApiResponse[list[SceneGroupRead]],
    summary="剧集场次列表",
)
async def list_scene_groups_api(
    chapter_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[SceneGroupRead]]:
    await get_chapter_in_workspace(db, chapter_id, ctx)
    return success_response(await list_groups(db, chapter_id=chapter_id))


@router.post(
    "/chapters/{chapter_id}/scene-groups",
    response_model=ApiResponse[SceneGroupRead],
    status_code=status.HTTP_201_CREATED,
    summary="创建场次",
)
async def create_scene_group_api(
    chapter_id: str,
    body: SceneGroupCreate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[SceneGroupRead]:
    await get_chapter_in_workspace(db, chapter_id, ctx)
    try:
        data = await create_group(
            db, chapter_id=chapter_id, body=body, created_by=ctx.user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return created_response(data)


@router.get(
    "/scene-groups/{group_id}",
    response_model=ApiResponse[SceneGroupRead],
    summary="场次详情",
)
async def get_scene_group_api(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[SceneGroupRead]:
    await get_scene_group_in_workspace(db, group_id, ctx)
    return success_response(await get_group(db, group_id=group_id))


@router.patch(
    "/scene-groups/{group_id}",
    response_model=ApiResponse[SceneGroupRead],
    summary="修改场次",
)
async def update_scene_group_api(
    group_id: str,
    body: SceneGroupUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[SceneGroupRead]:
    await get_scene_group_in_workspace(db, group_id, ctx)
    try:
        data = await update_group(db, group_id=group_id, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.delete(
    "/scene-groups/{group_id}",
    response_model=ApiResponse[None],
    summary="删除空场次",
)
async def delete_scene_group_api(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[None]:
    await get_scene_group_in_workspace(db, group_id, ctx)
    try:
        await delete_group(db, group_id=group_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return empty_response()


@router.post(
    "/chapters/{chapter_id}/scene-groups/reorder",
    response_model=ApiResponse[list[SceneGroupRead]],
    summary="场次排序",
)
async def reorder_scene_groups_api(
    chapter_id: str,
    body: SceneGroupReorderRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[list[SceneGroupRead]]:
    await get_chapter_in_workspace(db, chapter_id, ctx)
    try:
        data = await reorder_groups(db, chapter_id=chapter_id, group_ids=body.group_ids)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.get(
    "/scene-groups/{group_id}/shots",
    response_model=ApiResponse[list[ShotRead]],
    summary="场次镜头列表",
)
async def list_scene_group_shots_api(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[ShotRead]]:
    await get_scene_group_in_workspace(db, group_id, ctx)
    return success_response(await list_group_shots(db, group_id=group_id))


@router.post(
    "/chapters/{chapter_id}/shots/reorder",
    response_model=ApiResponse[list[ShotRead]],
    summary="章节镜头跨场次排序/移动",
)
async def reorder_chapter_shots_api(
    chapter_id: str,
    body: ShotReorderRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[list[ShotRead]]:
    await get_chapter_in_workspace(db, chapter_id, ctx)
    try:
        data = await reorder_chapter_shots(
            db, chapter_id=chapter_id, items=body.items
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.get(
    "/chapters/{chapter_id}/scene-group-suggestions",
    response_model=ApiResponse[SceneGroupSuggestionRead],
    summary="P3 场次建议与场次规划来源",
)
async def get_scene_group_suggestions_api(
    chapter_id: str,
    parse_run_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[SceneGroupSuggestionRead]:
    await get_chapter_in_workspace(db, chapter_id, ctx)
    return success_response(
        await get_scene_group_suggestions(
            db, chapter_id=chapter_id, parse_run_id=parse_run_id
        )
    )


@router.post(
    "/chapters/{chapter_id}/scene-groups/import",
    response_model=ApiResponse[SceneGroupImportRead],
    status_code=status.HTTP_201_CREATED,
    summary="导入 P3 场次建议（幂等）",
)
async def import_scene_group_suggestions_api(
    chapter_id: str,
    body: SceneGroupImportRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[SceneGroupImportRead]:
    await get_chapter_in_workspace(db, chapter_id, ctx)
    try:
        data = await import_scene_group_suggestions(
            db,
            chapter_id=chapter_id,
            parse_run_id=body.parse_run_id,
            items=body.items,
            skip_existing=body.skip_existing,
            created_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return created_response(data)
