"""文本模型 token 用量日志。

为什么需要：真实付费验收必须能回答“这次调用花了多少 token”，
而 LangChain 的 usage 默认只挂在响应对象上，业务层拿到的是 Pydantic/字符串。
这里用回调把 usage 写入应用日志，便于按 trace/时间对账；不记录 Key、Prompt 或响应正文。
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


class UsageLoggingCallback(BaseCallbackHandler):
    """只记录 token usage 的轻量回调。"""

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:  # noqa: ANN401
        try:
            llm_output = getattr(response, "llm_output", None) or {}
            usage = llm_output.get("token_usage") or llm_output.get("usage") or {}
            if not usage:
                # 部分网关把 usage 放在 generations[0].message.usage_metadata
                generations = getattr(response, "generations", None) or []
                message = generations[0][0].message if generations and generations[0] else None
                usage = getattr(message, "usage_metadata", None) or {}
            if usage:
                logger.info(
                    "llm_usage model=%s input=%s output=%s total=%s",
                    llm_output.get("model_name") or llm_output.get("model") or "unknown",
                    usage.get("prompt_tokens") or usage.get("input_tokens"),
                    usage.get("completion_tokens") or usage.get("output_tokens"),
                    usage.get("total_tokens"),
                )
        except Exception:  # noqa: BLE001 - 用量日志绝不能影响业务调用
            logger.debug("failed to log llm usage", exc_info=True)
