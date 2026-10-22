"""给 Celery worker 使用的同步 LLM runtime。"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from app.models.llm import Model, ModelCategoryKey, ModelSettings, Provider
from app.services.llm.provider_registry import (
    extra_headers_for_provider,
    thinking_extra_body_for_provider_name,
)
from app.services.llm.provider_resolver import resolve_effective_base_url


def _default_model_id(settings_row: ModelSettings | None, category: ModelCategoryKey) -> str | None:
    if settings_row is None:
        return None
    if category == ModelCategoryKey.text:
        return settings_row.default_text_model_id
    if category == ModelCategoryKey.image:
        return settings_row.default_image_model_id
    return settings_row.default_video_model_id


def _require_provider_and_model_sync(
    db: Session,
    *,
    category: ModelCategoryKey,
    model_id: str | None = None,
) -> tuple[Provider, Model]:
    settings_row = db.get(ModelSettings, 1)
    resolved_model_id = model_id or _default_model_id(settings_row, category)
    if not resolved_model_id:
        raise HTTPException(status_code=503, detail=f"No default model configured for category={category.value}")

    model = db.get(Model, resolved_model_id)
    if model is None:
        raise HTTPException(status_code=503, detail=f"Configured default model not found: {resolved_model_id}")
    if model.category != category:
        raise HTTPException(
            status_code=503,
            detail=f"Configured model is not {category.value} category: {resolved_model_id}",
        )

    provider = db.get(Provider, model.provider_id)
    if provider is None:
        raise HTTPException(status_code=503, detail=f"Provider not found for model_id={model.id}")

    return provider, model


def _build_text_llm_sync(
    *,
    provider: Provider,
    model: Model,
    thinking: bool,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> BaseChatModel:
    """按 provider/model 构造 ChatOpenAI；timeout/max_retries 可选。"""
    api_key = (provider.api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail=f"Provider api_key is empty for provider_id={provider.id}")

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise HTTPException(status_code=503, detail="Install langchain-openai to enable script-processing tasks") from e

    kwargs: dict[str, Any] = dict(model.params or {})
    kwargs["model"] = model.name
    kwargs["api_key"] = api_key
    kwargs.setdefault("temperature", 0)
    if timeout is not None:
        kwargs["timeout"] = float(timeout)
    if max_retries is not None:
        kwargs["max_retries"] = int(max_retries)

    base_url = resolve_effective_base_url(provider=provider, category=ModelCategoryKey.text)
    if base_url:
        kwargs.setdefault("base_url", base_url)

    # OpenCode Zen 等网关要求的额外请求头（缺失会直接 400 MissingSessionID）。
    extra_headers = extra_headers_for_provider(provider.name, base_url)
    if extra_headers:
        kwargs["default_headers"] = {**(kwargs.get("default_headers") or {}), **extra_headers}

    # 思考开关按供应商下发（阿里百炼 enable_thinking / DeepSeek thinking），未登记供应商不下发。
    thinking_body = thinking_extra_body_for_provider_name(provider.name, enabled=thinking)
    if thinking_body:
        extra_body = dict(kwargs.get("extra_body") or {})
        extra_body.update(thinking_body)
        kwargs["extra_body"] = extra_body

    return ChatOpenAI(**kwargs)


def build_text_llm_sync(
    db: Session,
    *,
    model_id: str | None = None,
    thinking: bool,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> BaseChatModel:
    """按显式 model_id 或默认文本模型构造 LLM。"""
    provider, model = _require_provider_and_model_sync(
        db,
        category=ModelCategoryKey.text,
        model_id=model_id,
    )
    return _build_text_llm_sync(
        provider=provider,
        model=model,
        thinking=thinking,
        timeout=timeout,
        max_retries=max_retries,
    )


def build_default_text_llm_sync(
    db: Session,
    *,
    thinking: bool,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> BaseChatModel:
    """构造默认文本模型。"""
    return build_text_llm_sync(
        db,
        thinking=thinking,
        timeout=timeout,
        max_retries=max_retries,
    )


def build_fallback_text_llm_sync(
    db: Session,
    *,
    thinking: bool,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> BaseChatModel | None:
    """构造备用文本模型；未配置或与默认模型相同则返回 None。"""
    if db is None:  # 单元测试/极端降级路径：没有 DB 就没有备用模型
        return None
    settings_row = db.get(ModelSettings, 1)
    fallback_id = settings_row.fallback_text_model_id if settings_row else None
    if not fallback_id:
        return None
    default_id = settings_row.default_text_model_id if settings_row else None
    if default_id and fallback_id == default_id:
        return None
    try:
        return build_text_llm_sync(
            db,
            model_id=fallback_id,
            thinking=thinking,
            timeout=timeout,
            max_retries=max_retries,
        )
    except HTTPException:
        return None
