"""P6 / C13：视频批量任务 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.scoping import get_chapter_in_workspace
from app.dependencies import WorkspaceContext, get_db, require_editor, require_viewer
from app.models.studio import Project, VideoGenerationBatch
from app.schemas.common import ApiResponse, created_response, success_response
from app.schemas.studio.video_batches import (
    VideoBatchCreate,
    VideoBatchListRead,
    VideoBatchRead,
    VideoBatchRetryRequest,
)
from app.services.studio.video_batches import (
    cancel_batch,
    create_video_batch,
    get_batch,
    list_batches,
    retry_failed,
)

router = APIRouter()


async def _batch_in_workspace(
    db: AsyncSession, *, batch_id: str, workspace_id: str
) -> VideoGenerationBatch:
    row = await db.scalar(
        select(VideoGenerationBatch)
        .join(Project, Project.id == VideoGenerationBatch.project_id)
        .options(selectinload(VideoGenerationBatch.items))
        .where(
            VideoGenerationBatch.id == batch_id,
            Project.workspace_id == workspace_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Video batch not found")
    return row


@router.post(
    "/chapters/{chapter_id}/video-batches",
    response_model=ApiResponse[VideoBatchRead],
    status_code=status.HTTP_201_CREATED,
    summary="创建视频批量生成批次",
)
async def create_video_batch_api(
    chapter_id: str,
    body: VideoBatchCreate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[VideoBatchRead]:
    chapter = await get_chapter_in_workspace(db, chapter_id, ctx)
    project = await db.get(Project, chapter.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        batch = await create_video_batch(
            db, chapter=chapter, project=project, body=body, requested_by=ctx.user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return created_response(VideoBatchRead.model_validate(batch))


@router.get(
    "/chapters/{chapter_id}/video-batches",
    response_model=ApiResponse[VideoBatchListRead],
    summary="剧集视频批次列表",
)
async def list_video_batches_api(
    chapter_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[VideoBatchListRead]:
    await get_chapter_in_workspace(db, chapter_id, ctx)
    rows = await list_batches(db, chapter_id=chapter_id)
    return success_response(
        VideoBatchListRead(items=[VideoBatchRead.model_validate(item) for item in rows])
    )


@router.get(
    "/video-batches/{batch_id}",
    response_model=ApiResponse[VideoBatchRead],
    summary="批次状态与子任务",
)
async def get_video_batch_api(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[VideoBatchRead]:
    batch = await _batch_in_workspace(
        db, batch_id=batch_id, workspace_id=ctx.workspace_id
    )
    return success_response(VideoBatchRead.model_validate(batch))


@router.post(
    "/video-batches/{batch_id}/cancel",
    response_model=ApiResponse[VideoBatchRead],
    summary="取消批次（请求取消正在运行的子任务）",
)
async def cancel_video_batch_api(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[VideoBatchRead]:
    await _batch_in_workspace(db, batch_id=batch_id, workspace_id=ctx.workspace_id)
    try:
        batch = await cancel_batch(db, batch_id=batch_id, reason="user cancelled")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(VideoBatchRead.model_validate(batch))


@router.post(
    "/video-batches/{batch_id}/retry",
    response_model=ApiResponse[VideoBatchRead],
    summary="重试失败子任务",
)
async def retry_video_batch_api(
    batch_id: str,
    body: VideoBatchRetryRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[VideoBatchRead]:
    await _batch_in_workspace(db, batch_id=batch_id, workspace_id=ctx.workspace_id)
    try:
        batch = await retry_failed(db, batch_id=batch_id, item_ids=body.item_ids)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(VideoBatchRead.model_validate(batch))


@router.post(
    "/video-batches/{batch_id}/resume",
    response_model=ApiResponse[VideoBatchRead],
    summary="恢复批次协调器（Worker/API 重启后）",
)
async def resume_video_batch_api(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[VideoBatchRead]:
    batch = await _batch_in_workspace(
        db, batch_id=batch_id, workspace_id=ctx.workspace_id
    )
    if batch.coordinator_task_id:
        from app.tasks.execute_task import enqueue_task_execution

        enqueue_task_execution(batch.coordinator_task_id)
    return success_response(VideoBatchRead.model_validate(batch))
