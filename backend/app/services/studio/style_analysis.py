"""P2 / C4：风格参考图的结构化视觉分析。

复用现有文本供应商基础设施（`build_text_llm`）与对象存储：
- 不新建模型调用框架；
- 没有可用视觉/文本模型时返回明确提示；
- 分析结果不落库，由调用方人工修订后再保存，避免 AI 结果覆盖人工草稿。
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.models.llm import ModelCategoryKey
from app.models.studio import FileItem
from app.models.types import FileType
from app.schemas.studio.project_style import (
    StyleAnalysisCapabilityRead,
    StyleAnalysisRead,
)
from app.schemas.studio.projects import StyleStructuredProfile
from app.services.llm.resolver import (
    build_text_llm,
    get_model_by_category,
    get_provider_by_model_or_id,
)
from app.services.studio.style_catalog import build_prompt_pack_from_profile

_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

_SYSTEM_PROMPT = """你是短剧视觉风格分析师。请根据用户提供的 1–3 张风格参考图，输出结构化视觉特征。
只输出一个 JSON 对象，不要 markdown 代码块，不要解释。字段必须齐全，值使用简洁中文：
{
  "medium": "视觉媒介",
  "texture": "画面质感",
  "color": "色彩与饱和度",
  "lighting": "光照方式",
  "material": "材质特征",
  "character_rendering": "人物渲染特征",
  "scene_rendering": "场景渲染特征",
  "camera": "摄影与运镜风格",
  "keep": "应当保持的视觉特征",
  "avoid": "禁止出现的风格特征"
}
只描述画面中可观察的特征，不要写抽象评价词，不要编造参考图中不存在的信息。"""


async def get_style_analysis_capability(
    db: AsyncSession, *, model_id: str | None = None
) -> StyleAnalysisCapabilityRead:
    """检查当前是否有可用于视觉分析的文本模型。"""
    try:
        model = await get_model_by_category(
            db,
            ModelCategoryKey.text,
            model_or_id=model_id,
            allow_default_fallback=True,
        )
        provider = await get_provider_by_model_or_id(db, model)
    except HTTPException as exc:
        return StyleAnalysisCapabilityRead(available=False, reason=str(exc.detail))
    except Exception as exc:  # noqa: BLE001
        return StyleAnalysisCapabilityRead(available=False, reason=str(exc))

    if not (provider.api_key or "").strip():
        return StyleAnalysisCapabilityRead(
            available=False,
            model_id=model.id,
            model_name=model.name,
            provider_name=provider.name,
            reason=f"供应商「{provider.name}」未配置 API Key",
        )

    return StyleAnalysisCapabilityRead(
        available=True,
        model_id=model.id,
        model_name=model.name,
        provider_name=provider.name,
        reason="",
    )


async def _load_image_data_urls(db: AsyncSession, file_ids: list[str]) -> list[str]:
    """把风格参考图读成 data URL；文件不存在或不是图片时给出可执行错误。"""
    if not 1 <= len(file_ids) <= 3:
        raise ValueError("风格参考图需要 1–3 张")

    data_urls: list[str] = []
    for file_id in file_ids:
        file_item = await db.get(FileItem, file_id)
        if file_item is None:
            raise ValueError(f"风格参考图不存在：{file_id}")
        if file_item.type != FileType.image:
            raise ValueError(f"风格参考图必须是图片：{file_id}")
        content = await storage.download_file(key=file_item.storage_key)
        suffix = Path(file_item.name or file_item.storage_key).suffix.lower()
        mime = _MIME_BY_SUFFIX.get(suffix, "image/png")
        encoded = base64.b64encode(content).decode("ascii")
        data_urls.append(f"data:{mime};base64,{encoded}")
    return data_urls


def _parse_analysis_json(raw: str) -> dict[str, Any]:
    """解析模型输出；容忍 markdown 代码块，但不接受非 JSON。"""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("AI 返回内容不是有效 JSON")
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("AI 返回内容无法解析为 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("AI 返回内容不是 JSON 对象")
    return payload


def _normalize_profile(payload: dict[str, Any]) -> StyleStructuredProfile:
    fields = StyleStructuredProfile.model_fields.keys()
    return StyleStructuredProfile(
        **{
            key: str(payload.get(key) or "").strip()
            for key in fields
        }
    )


async def _invoke_style_analysis(
    chat_model: Any,
    *,
    messages: list[Any],
) -> str:
    """实际调用模型。

    单独抽成函数：测试可替换它，不触发任何真实付费调用。
    """
    response = await chat_model.ainvoke(messages)
    content = getattr(response, "content", response)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


async def analyze_style_images(
    db: AsyncSession,
    *,
    file_ids: list[str],
    model_id: str | None = None,
) -> StyleAnalysisRead:
    """分析风格参考图并返回结构化字段；不写库。"""
    if not 1 <= len(file_ids) <= 3:
        raise ValueError("风格参考图需要 1–3 张")

    data_urls = await _load_image_data_urls(db, file_ids)
    try:
        chat_model, model, provider = await build_text_llm(
            db, model_id=model_id, thinking=False
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"没有可用的视觉分析模型：{exc}") from exc

    content: list[dict[str, Any]] = [
        {"type": "text", "text": "请分析以下风格参考图，并按系统要求输出 JSON。"}
    ]
    content.extend(
        {"type": "image_url", "image_url": {"url": data_url}} for data_url in data_urls
    )
    messages = [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=content)]
    raw = await _invoke_style_analysis(chat_model, messages=messages)
    profile = _normalize_profile(_parse_analysis_json(raw))

    return StyleAnalysisRead(
        profile=profile,
        prompt_pack=build_prompt_pack_from_profile(profile.model_dump()),
        model_id=model.id,
        model_name=model.name,
        provider_name=provider.name,
        image_count=len(data_urls),
    )
