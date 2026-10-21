"""健康检查（v1 内）。"""

from fastapi import APIRouter

from app.schemas.common import ApiResponse, success_response

router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict])
async def v1_health() -> ApiResponse[dict]:
    return success_response(data={"status": "ok", "version": "v1"})
