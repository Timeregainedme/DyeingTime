"""创作工作台首页聚合接口。

只读接口：不触发任何生成、不写库。真正的统计口径在
`app.services.studio.dashboard`，本层只负责鉴权与响应封装。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import WorkspaceContext, get_db, require_viewer
from app.schemas.common import ApiResponse, success_response
from app.schemas.studio.dashboard import DashboardRead
from app.services.studio.dashboard import build_dashboard

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=ApiResponse[DashboardRead],
    summary="获取创作工作台首页聚合数据",
)
async def get_dashboard_api(
    db: AsyncSession = Depends(get_db),
    ctx: WorkspaceContext = Depends(require_viewer),
) -> ApiResponse[DashboardRead]:
    """一次返回项目、章节、镜头、任务与待审核快照（按当前工作区隔离）。"""
    data = await build_dashboard(db, ctx=ctx)
    return success_response(data)
