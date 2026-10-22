"""P4 / C8：资产变更影响分析 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.scoping import get_project_in_workspace
from app.dependencies import WorkspaceContext, get_db, require_viewer
from app.schemas.common import ApiResponse, success_response
from app.schemas.studio.asset_versions import (
    AssetImpactRead,
    AssetVersionImpactRefRead,
)
from app.services.studio.asset_impact import analyze_asset_impact, list_impact_refs
from app.services.studio.asset_versions import (
    asset_belongs_to_project,
    normalize_asset_type,
)

router = APIRouter()


@router.get(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/impact",
    response_model=ApiResponse[AssetImpactRead],
    summary="资产引用与受影响镜头",
)
async def get_asset_impact_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    from_version_id: str | None = Query(None),
    to_version_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[AssetImpactRead]:
    await get_project_in_workspace(db, project_id, ctx)
    try:
        normalized = normalize_asset_type(asset_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not await asset_belongs_to_project(
        db, asset_type=normalized, asset_id=asset_id, project_id=project_id
    ):
        raise HTTPException(status_code=404, detail="Asset not found in project")
    return success_response(
        await analyze_asset_impact(
            db,
            project_id=project_id,
            asset_type=normalized,
            asset_id=asset_id,
            from_version_id=from_version_id,
            to_version_id=to_version_id,
        )
    )


@router.get(
    "/projects/{project_id}/assets/{asset_type}/{asset_id}/impact-history",
    response_model=ApiResponse[list[AssetVersionImpactRefRead]],
    summary="资产版本切换影响历史",
)
async def list_asset_impact_history_api(
    project_id: str,
    asset_type: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[AssetVersionImpactRefRead]]:
    await get_project_in_workspace(db, project_id, ctx)
    try:
        normalized = normalize_asset_type(asset_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not await asset_belongs_to_project(
        db, asset_type=normalized, asset_id=asset_id, project_id=project_id
    ):
        raise HTTPException(status_code=404, detail="Asset not found in project")
    return success_response(
        await list_impact_refs(
            db, project_id=project_id, asset_type=normalized, asset_id=asset_id
        )
    )
