"""剧本优化 Agent：ScriptOptimizerAgent"""

from __future__ import annotations

from typing import Any

from langchain_core.prompts import PromptTemplate

from app.chains.agents.base import AgentBase
from app.schemas.skills.script_processing import ScriptOptimizationResult

_SCRIPT_OPTIMIZER_SYSTEM_PROMPT = """\
你是\"剧本优化师\"。仅当一致性检查发现角色混淆问题时，对原文进行最小改写以消除混淆。

输入：
- script_text：原文
- consistency_json：一致性检查输出（ScriptConsistencyCheckResult）

输出 ScriptOptimizationResult：
- optimized_script_text：优化后的完整剧本文本（尽量少改，只改与 issues 相关的段落）
- change_summary：改动摘要，必须是字符串（不是数组/对象）；多条改动请拼接成一段文本

只输出 JSON。
"""

SCRIPT_OPTIMIZER_PROMPT = PromptTemplate(
    input_variables=["script_text", "consistency_json"],
    template="## 一致性检查结果\n{consistency_json}\n\n## 原文剧本\n{script_text}\n\n## 输出\n",
)


class ScriptOptimizerAgent(AgentBase[ScriptOptimizationResult]):

    """剧本优化 Agent：输入一致性检查输出 + 原文，输出优化后的剧本。"""

    # 注册表键：发布后的模板提示词覆盖代码默认（见 prompt_registry.py）
    agent_key = 'script_optimize'

    def _default_system_prompt(self) -> str:
        return _SCRIPT_OPTIMIZER_SYSTEM_PROMPT

    @property
    def prompt_template(self) -> PromptTemplate:
        return SCRIPT_OPTIMIZER_PROMPT

    @property
    def output_model(self) -> type[ScriptOptimizationResult]:
        return ScriptOptimizationResult

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        data = dict(data)
        if "optimized_script_text" not in data:
            data["optimized_script_text"] = ""
        if "change_summary" not in data:
            data["change_summary"] = ""
        # 模型偶尔会把改动摘要输出为 issue 对象列表，这里先归一化为文本，避免 Pydantic 校验失败
        change_summary = data.get("change_summary")
        if isinstance(change_summary, list):
            parts: list[str] = []
            for item in change_summary:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    issue_type = item.get("issue_type") or item.get("type")
                    description = item.get("description") or item.get("summary") or item.get("change")
                    suggestion = item.get("suggestion") or item.get("fix")
                    text = "：".join(str(x) for x in (issue_type, description) if x)
                    if suggestion:
                        text = f"{text}（建议：{suggestion}）" if text else f"建议：{suggestion}"
                    parts.append(text or str(item))
                else:
                    parts.append(str(item))
            data["change_summary"] = "\n".join(part for part in parts if part)
        elif change_summary is not None and not isinstance(change_summary, str):
            data["change_summary"] = str(change_summary)
        if not isinstance(data.get("optimized_script_text"), str):
            data["optimized_script_text"] = str(data.get("optimized_script_text") or "")
        return data

