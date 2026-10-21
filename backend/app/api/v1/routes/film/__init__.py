"""影视技能 API：实体抽取、分镜抽取。"""

from __future__ import annotations


from fastapi import APIRouter

from app.api.v1.routes.film import generated_video, tasks_images, task_status

router = APIRouter()
router.include_router(generated_video.router)
router.include_router(tasks_images.router)
router.include_router(task_status.router)

__all__ = ["router"]
