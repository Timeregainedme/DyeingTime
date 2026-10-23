"""P5 / C10：AI 分镜规划草稿与镜头资产版本 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.scoping import get_chapter_in_workspace, get_shot_in_workspace
from app.dependencies import WorkspaceContext, get_db, require_editor, require_viewer
from app.models.studio import Project, ShotPlanDraft
from app.schemas.common import ApiResponse, created_response, empty_response, success_response
from app.schemas.studio.shot_plans import (
    ShotAssetVersionRead,
    ShotPlanCandidateCreate,
    ShotPlanCandidateRead,
    ShotPlanCandidateUpdate,
    ShotPlanConfirmRead,
    ShotPlanConfirmRequest,
    ShotPlanDraftRead,
    ShotPlanMergeRequest,
    ShotPlanRequest,
    ShotPlanReorderRequest,
    ShotPlanStatsRead,
)
from app.services.studio.shot_plans import (
    add_candidate,
    confirm_draft,
    create_shot_plan,
    delete_candidate,
    duplicate_candidate,
    draft_to_read,
    get_draft,
    get_stats,
    list_drafts,
    list_shot_asset_versions,
    merge_candidates,
    reorder_candidates,
    update_candidate,
)

router = APIRouter()


async def _draft_in_workspace(
    db: AsyncSession, *, draft_id: str, workspace_id: str
) -> ShotPlanDraft:
    draft = await db.scalar(
        select(ShotPlanDraft)
        .join(Project, Project.id == ShotPlanDraft.project_id)
        .options(selectinload(ShotPlanDraft.candidates))
        .where(
            ShotPlanDraft.id == draft_id,
            Project.workspace_id == workspace_id,
        )
    )
    if draft is None:
        raise HTTPException(status_code=404, detail="ShotPlan draft not found")
    return draft


@router.post(
    "/chapters/{chapter_id}/shot-plans",
    response_model=ApiResponse[ShotPlanDraftRead],
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建 AI 分镜规划任务",
)
async def create_shot_plan_api(
    chapter_id: str,
    body: ShotPlanRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ShotPlanDraftRead]:
    chapter = await get_chapter_in_workspace(db, chapter_id, ctx)
    project = await db.get(Project, chapter.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        draft, reused = await create_shot_plan(
            db, chapter=chapter, project=project, body=body, created_by=ctx.user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _ = reused
    return success_response(draft_to_read(draft))


@router.get(
    "/chapters/{chapter_id}/shot-plans",
    response_model=ApiResponse[list[ShotPlanDraftRead]],
    summary="剧集分镜规划历史",
)
async def list_shot_plans_api(
    chapter_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[ShotPlanDraftRead]]:
    await get_chapter_in_workspace(db, chapter_id, ctx)
    return success_response(await list_drafts(db, chapter_id=chapter_id))


@router.get(
    "/chapters/{chapter_id}/shot-plan-stats",
    response_model=ApiResponse[ShotPlanStatsRead],
    summary="剧集分镜规划统计",
)
async def get_shot_plan_stats_api(
    chapter_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[ShotPlanStatsRead]:
    await get_chapter_in_workspace(db, chapter_id, ctx)
    return success_response(await get_stats(db, chapter_id=chapter_id))


@router.get(
    "/shot-plans/{draft_id}",
    response_model=ApiResponse[ShotPlanDraftRead],
    summary="分镜规划草稿详情",
)
async def get_shot_plan_api(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[ShotPlanDraftRead]:
    await _draft_in_workspace(db, draft_id=draft_id, workspace_id=ctx.workspace_id)
    return success_response(await get_draft(db, draft_id=draft_id))


@router.patch(
    "/shot-plans/{draft_id}/candidates/{candidate_id}",
    response_model=ApiResponse[ShotPlanCandidateRead],
    summary="编辑/接受/忽略分镜候选",
)
async def update_shot_plan_candidate_api(
    draft_id: str,
    candidate_id: str,
    body: ShotPlanCandidateUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ShotPlanCandidateRead]:
    await _draft_in_workspace(db, draft_id=draft_id, workspace_id=ctx.workspace_id)
    try:
        data = await update_candidate(
            db, draft_id=draft_id, candidate_id=candidate_id, body=body
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.post(
    "/shot-plans/{draft_id}/candidates",
    response_model=ApiResponse[ShotPlanCandidateRead],
    status_code=status.HTTP_201_CREATED,
    summary="人工新增分镜候选",
)
async def add_shot_plan_candidate_api(
    draft_id: str,
    body: ShotPlanCandidateCreate,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ShotPlanCandidateRead]:
    await _draft_in_workspace(db, draft_id=draft_id, workspace_id=ctx.workspace_id)
    try:
        data = await add_candidate(db, draft_id=draft_id, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return created_response(data)


@router.post(
    "/shot-plans/{draft_id}/candidates/{candidate_id}/duplicate",
    response_model=ApiResponse[ShotPlanCandidateRead],
    status_code=status.HTTP_201_CREATED,
    summary="复制镜头候选（用于拆分）",
)
async def duplicate_shot_plan_candidate_api(
    draft_id: str,
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ShotPlanCandidateRead]:
    await _draft_in_workspace(db, draft_id=draft_id, workspace_id=ctx.workspace_id)
    try:
        data = await duplicate_candidate(
            db, draft_id=draft_id, candidate_id=candidate_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return created_response(data)


@router.delete(
    "/shot-plans/{draft_id}/candidates/{candidate_id}",
    response_model=ApiResponse[None],
    summary="删除镜头候选",
)
async def delete_shot_plan_candidate_api(
    draft_id: str,
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[None]:
    await _draft_in_workspace(db, draft_id=draft_id, workspace_id=ctx.workspace_id)
    try:
        await delete_candidate(db, draft_id=draft_id, candidate_id=candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return empty_response()


@router.post(
    "/shot-plans/{draft_id}/reorder",
    response_model=ApiResponse[ShotPlanDraftRead],
    summary="镜头候选排序",
)
async def reorder_shot_plan_candidates_api(
    draft_id: str,
    body: ShotPlanReorderRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ShotPlanDraftRead]:
    await _draft_in_workspace(db, draft_id=draft_id, workspace_id=ctx.workspace_id)
    try:
        data = await reorder_candidates(
            db, draft_id=draft_id, candidate_ids=body.candidate_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.post(
    "/shot-plans/{draft_id}/merge",
    response_model=ApiResponse[ShotPlanCandidateRead],
    summary="合并相邻镜头候选",
)
async def merge_shot_plan_candidates_api(
    draft_id: str,
    body: ShotPlanMergeRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ShotPlanCandidateRead]:
    await _draft_in_workspace(db, draft_id=draft_id, workspace_id=ctx.workspace_id)
    try:
        data = await merge_candidates(
            db,
            draft_id=draft_id,
            source_id=body.source_candidate_id,
            target_id=body.target_candidate_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(data)


@router.post(
    "/shot-plans/{draft_id}/confirm",
    response_model=ApiResponse[ShotPlanConfirmRead],
    summary="应用确认后的分镜规划",
)
async def confirm_shot_plan_api(
    draft_id: str,
    body: ShotPlanConfirmRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[ShotPlanConfirmRead]:
    draft = await _draft_in_workspace(
        db, draft_id=draft_id, workspace_id=ctx.workspace_id
    )
    try:
        draft, shot_ids, reused, warnings = await confirm_draft(
            db,
            draft=draft,
            append_to_existing=body.append_to_existing,
            applied_by=ctx.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(
        ShotPlanConfirmRead(
            draft=draft_to_read(draft),
            shot_ids=shot_ids,
            reused=reused,
            warnings=warnings,
        )
    )


@router.get(
    "/shots/{shot_id}/asset-versions",
    response_model=ApiResponse[list[ShotAssetVersionRead]],
    summary="镜头资产版本选择",
)
async def list_shot_asset_versions_api(
    shot_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[ShotAssetVersionRead]]:
    await get_shot_in_workspace(db, shot_id, ctx)
    return success_response(await list_shot_asset_versions(db, shot_id=shot_id))
