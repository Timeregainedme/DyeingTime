"""P6 / C11：镜头参考绑定、@ 引用、生成预览与快照 API。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.scoping import get_shot_in_workspace
from app.dependencies import WorkspaceContext, get_db, require_editor, require_viewer
from app.models.studio import ShotGenerationSnapshot
from app.schemas.common import ApiResponse, created_response, success_response
from app.schemas.studio.shots import ShotVideoReadinessRead
from app.schemas.studio.shot_references import (
    GenerationPreviewRead,
    GenerationSnapshotRead,
    P6VideoGenerateRequest,
    P6VideoTaskCreated,
    PromptReferenceRead,
    PromptResolveRead,
    PromptResolveRequest,
    ReferenceBindingRead,
    ReferenceBindingReorder,
    ReferenceBindingUpdate,
    ShotPromptUpdate,
)
from app.services.studio.shot_references import (
    auto_recommend,
    build_generation_preview,
    create_video_task,
    get_p6_readiness,
    list_bindings,
    list_snapshots,
    remove_binding,
    reorder_bindings,
    resolve_prompt_references,
    save_prompt,
    snapshot_to_read,
    update_binding,
    upload_reference,
)

router = APIRouter()


@router.get(
    "/shots/{shot_id}/p6-readiness",
    response_model=ApiResponse[ShotVideoReadinessRead],
    summary="P6 H3 多参考生成准备度",
)
async def get_p6_readiness_api(
    shot_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
):
    await get_shot_in_workspace(db, shot_id, ctx)
    return success_response(await get_p6_readiness(db, shot_id=shot_id))


@router.get(
    "/shots/{shot_id}/reference-bindings",
    response_model=ApiResponse[list[ReferenceBindingRead]],
    summary="镜头参考绑定列表",
)
async def list_reference_bindings_api(
    shot_id: str,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[ReferenceBindingRead]]:
    await get_shot_in_workspace(db, shot_id, ctx)
    return success_response(await list_bindings(db, shot_id=shot_id, active_only=active_only))


@router.post(
    "/shots/{shot_id}/reference-bindings/recommend",
    response_model=ApiResponse[list[ReferenceBindingRead]],
    summary="按 P5 资产版本自动推荐参考图",
)
async def recommend_reference_bindings_api(
    shot_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[list[ReferenceBindingRead]]:
    await get_shot_in_workspace(db, shot_id, ctx)
    try:
        data = await auto_recommend(db, shot_id=shot_id, created_by=ctx.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.patch(
    "/shots/{shot_id}/reference-bindings/{binding_id}",
    response_model=ApiResponse[ReferenceBindingRead],
    summary="修改参考图锁定/启停/用途",
)
async def update_reference_binding_api(
    shot_id: str,
    binding_id: int,
    body: ReferenceBindingUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ReferenceBindingRead]:
    await get_shot_in_workspace(db, shot_id, ctx)
    try:
        data = await update_binding(
            db,
            binding_id=binding_id,
            shot_id=shot_id,
            is_pinned=body.is_pinned,
            is_active=body.is_active,
            reference_role=body.reference_role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.delete(
    "/shots/{shot_id}/reference-bindings/{binding_id}",
    response_model=ApiResponse[None],
    summary="禁用参考图",
)
async def remove_reference_binding_api(
    shot_id: str,
    binding_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[None]:
    await get_shot_in_workspace(db, shot_id, ctx)
    try:
        await remove_binding(db, binding_id=binding_id, shot_id=shot_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    from app.schemas.common import empty_response

    return empty_response()


@router.post(
    "/shots/{shot_id}/reference-bindings/reorder",
    response_model=ApiResponse[list[ReferenceBindingRead]],
    summary="参考图排序",
)
async def reorder_reference_bindings_api(
    shot_id: str,
    body: ReferenceBindingReorder,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[list[ReferenceBindingRead]]:
    await get_shot_in_workspace(db, shot_id, ctx)
    try:
        data = await reorder_bindings(
            db, shot_id=shot_id, binding_ids=body.binding_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.post(
    "/shots/{shot_id}/reference-bindings/upload",
    response_model=ApiResponse[ReferenceBindingRead],
    status_code=status.HTTP_201_CREATED,
    summary="上传镜头专属参考图",
)
async def upload_reference_binding_api(
    shot_id: str,
    file: UploadFile = File(...),
    reference_role: str = "shot_composition",
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ReferenceBindingRead]:
    await get_shot_in_workspace(db, shot_id, ctx)
    try:
        data = await upload_reference(
            db,
            shot_id=shot_id,
            file=file,
            reference_role=reference_role,
            created_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return created_response(data)


@router.post(
    "/shots/{shot_id}/prompt/resolve",
    response_model=ApiResponse[PromptResolveRead],
    summary="解析 @ 资产引用",
)
async def resolve_prompt_api(
    shot_id: str,
    body: PromptResolveRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[PromptResolveRead]:
    await get_shot_in_workspace(db, shot_id, ctx)
    return success_response(
        await resolve_prompt_references(db, shot_id=shot_id, prompt=body.prompt)
    )


@router.put(
    "/shots/{shot_id}/prompt",
    response_model=ApiResponse[PromptResolveRead],
    summary="保存自然语言提示词与 @ 引用",
)
async def save_prompt_api(
    shot_id: str,
    body: ShotPromptUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[PromptResolveRead]:
    await get_shot_in_workspace(db, shot_id, ctx)
    return success_response(
        await save_prompt(db, shot_id=shot_id, prompt=body.prompt)
    )


@router.post(
    "/shots/{shot_id}/generation-preview",
    response_model=ApiResponse[GenerationPreviewRead],
    summary="预览 P6 H3 参考清单与最终提示词",
)
async def generation_preview_api(
    shot_id: str,
    body: P6VideoGenerateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[GenerationPreviewRead]:
    await get_shot_in_workspace(db, shot_id, ctx)
    try:
        data = await build_generation_preview(
            db,
            shot_id=shot_id,
            natural_prompt=body.prompt,
            advanced_prompt=body.advanced_prompt,
            reference_mode=body.reference_mode,
            ratio=body.ratio,
            resolution=body.resolution,
            reference_audio_file_ids=body.reference_audio_file_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.post(
    "/shots/{shot_id}/generation",
    response_model=ApiResponse[P6VideoTaskCreated],
    status_code=status.HTTP_201_CREATED,
    summary="创建 P6 单镜头视频任务（显式采纳）",
)
async def create_p6_video_task_api(
    shot_id: str,
    body: P6VideoGenerateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[P6VideoTaskCreated]:
    await get_shot_in_workspace(db, shot_id, ctx)
    try:
        task_id, snapshot, preview = await create_video_task(
            db, shot_id=shot_id, body=body, created_by=ctx.user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return created_response(
        P6VideoTaskCreated(
            task_id=task_id,
            snapshot_id=snapshot.id,
            preview=preview,
        )
    )


@router.get(
    "/shots/{shot_id}/generation-snapshots",
    response_model=ApiResponse[list[GenerationSnapshotRead]],
    summary="镜头生成输入快照历史",
)
async def list_generation_snapshots_api(
    shot_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[GenerationSnapshotRead]]:
    await get_shot_in_workspace(db, shot_id, ctx)
    rows = await list_snapshots(db, shot_id=shot_id)
    return success_response([await snapshot_to_read(db, item) for item in rows])


@router.get(
    "/generation-snapshots/{snapshot_id}",
    response_model=ApiResponse[GenerationSnapshotRead],
    summary="生成输入快照详情",
)
async def get_generation_snapshot_api(
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[GenerationSnapshotRead]:
    snapshot = await db.get(ShotGenerationSnapshot, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Generation snapshot not found")
    await get_shot_in_workspace(db, snapshot.shot_id, ctx)
    return success_response(await snapshot_to_read(db, snapshot))
