from __future__ import annotations

"""Studio 音频（TTS）任务的数据层能力。

与 `image_tasks.py` 对称：按 audio 类别解析模型与供应商配置。
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.contracts.provider import ProviderConfig
from app.models.llm import Model, ModelCategoryKey
from app.services.llm import get_model_by_category
from app.services.llm.provider_resolver import resolve_provider_config
from app.services.studio.project_generation_config import resolve_project_model


async def resolve_audio_model(
    db: AsyncSession,
    model_id: str | None,
    *,
    project_id: str | None = None,
) -> Model:
    """根据显式 model_id、项目快照或全局默认解析音频模型。"""
    if model_id is None and project_id:
        project_model = await resolve_project_model(
            db, project_id=project_id, category=ModelCategoryKey.audio
        )
        if project_model is not None:
            return project_model
    try:
        return await get_model_by_category(
            db,
            ModelCategoryKey.audio,
            model_or_id=model_id,
            allow_default_fallback=False,
        )
    except HTTPException as e:
        if e.status_code == status.HTTP_404_NOT_FOUND and model_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Configured model_id not found in DB: {model_id}",
            ) from e
        if e.status_code == status.HTTP_503_SERVICE_UNAVAILABLE and not model_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "No audio model configured in DB "
                    "(missing explicit model_id and ModelSettings.default_audio_model_id)"
                ),
            ) from e
        if e.status_code == status.HTTP_503_SERVICE_UNAVAILABLE and model_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Configured model is not an audio model: {model_id}",
            ) from e
        raise


async def load_audio_provider_config(db: AsyncSession, provider_id: str) -> ProviderConfig:
    """根据 provider_id 从 DB 解析音频能力的 ProviderConfig。"""
    resolved = await resolve_provider_config(
        db,
        provider_id=provider_id,
        category=ModelCategoryKey.audio,
    )
    return ProviderConfig(
        provider=resolved.provider_key,  # type: ignore[arg-type]
        api_key=resolved.api_key,
        base_url=resolved.base_url,
    )


__all__ = ["resolve_audio_model", "load_audio_provider_config"]
