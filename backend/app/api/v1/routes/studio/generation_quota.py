"""P6 / C12：测试额度查询/预留/结算 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_editor, require_viewer, WorkspaceContext
from app.models.studio import GenerationUsageReservation
from app.schemas.common import ApiResponse, success_response
from app.schemas.studio.generation_quota import (
    QuotaReservationRead,
    QuotaReserveRequest,
    QuotaSettleRequest,
    QuotaStatusRead,
)
from app.services.studio.generation_quota import (
    DEFAULT_SCOPE,
    QuotaExceeded,
    get_quota_status,
    list_reservations,
    reserve,
    settle,
)

router = APIRouter()


@router.get(
    "/generation-quota",
    response_model=ApiResponse[list[QuotaStatusRead]],
    summary="查询 V2 验收测试额度",
)
async def get_generation_quota_api(
    scope: str = DEFAULT_SCOPE,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[QuotaStatusRead]]:
    _ = ctx
    return success_response(await get_quota_status(db, scope=scope))


@router.get(
    "/generation-quota/reservations",
    response_model=ApiResponse[list[QuotaReservationRead]],
    summary="额度预留/结算记录",
)
async def list_generation_quota_reservations_api(
    scope: str = DEFAULT_SCOPE,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[list[QuotaReservationRead]]:
    _ = ctx
    rows = await list_reservations(db, scope=scope)
    return success_response([QuotaReservationRead.model_validate(item) for item in rows])


@router.post(
    "/generation-quota/reserve",
    response_model=ApiResponse[QuotaReservationRead],
    summary="原子预留测试额度（防并发超额）",
)
async def reserve_generation_quota_api(
    body: QuotaReserveRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[QuotaReservationRead]:
    _ = ctx
    try:
        row = await reserve(
            db,
            media_type=body.media_type,
            amount=body.amount,
            task_id=body.task_id,
            provider=body.provider,
            model=body.model,
            note=body.note,
        )
    except QuotaExceeded as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success_response(QuotaReservationRead.model_validate(row))


@router.post(
    "/generation-quota/settle",
    response_model=ApiResponse[QuotaReservationRead],
    summary="结算测试额度预留",
)
async def settle_generation_quota_api(
    body: QuotaSettleRequest,
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_editor),
) -> ApiResponse[QuotaReservationRead]:
    _ = ctx
    row = await db.get(GenerationUsageReservation, body.reservation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Quota reservation not found")
    row = await settle(db, row, commit=body.commit)
    return success_response(QuotaReservationRead.model_validate(row))
