"""P3 / C6：单集剧本结构化解析 Agent。

只负责「文本 + 世界观 + 已有实体 → 候选结构」，不写库、不合并业务实体。
长文分块与跨块合并由 `script_parse_runner` 负责。
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import PromptTemplate

from app.chains.agents.base import AgentBase, _extract_json_from_text
from app.schemas.skills.script_parse import ScriptParseResult

_EPISODE_PARSE_SYSTEM_PROMPT = """\
你是资深短剧剧本统筹。请把「项目世界观 + 本集剧本」解析为结构化候选，供人工审核。

只输出一个 JSON 对象，不要 markdown 代码块，不要解释。结构：
{
  "characters": [{
    "name": "", "aliases": [], "role": "", "age_range": "", "appearance": "",
    "hairstyle": "", "body_type": "", "base_costume": "", "voice_description": "",
    "episodes": [], "evidence": [{"chunk_id": "", "quote": ""}], "issues": []
  }],
  "scenes": [{
    "name": "", "location_type": "", "interior_exterior": "", "spatial_features": "",
    "time_light": "", "key_furnishings": "", "is_existing": false,
    "evidence": [{"chunk_id": "", "quote": ""}], "issues": []
  }],
  "props": [{
    "name": "", "appearance": "", "color_material": "", "story_usage": "",
    "holder_character": "", "location": "", "is_existing": false,
    "evidence": [{"chunk_id": "", "quote": ""}], "issues": []
  }],
  "costume_changes": [{
    "character_name": "", "base_costume": "", "changed_costume": "",
    "story_position": "", "reason": "", "applicable_episode": null,
    "suggested_scene": "", "evidence": [{"chunk_id": "", "quote": ""}], "issues": []
  }],
  "episode": {
    "title": "", "summary": "", "major_events": [],
    "scene_beats": [{
      "index": 1, "title": "", "location": "", "time_of_day": "",
      "characters": [], "events": [], "source_range": "",
      "evidence": [{"chunk_id": "", "quote": ""}], "issues": []
    }]
  },
  "dialogues": [{
    "text": "", "speaker_name": null, "order": 1, "emotion": "",
    "line_mode": "DIALOGUE", "story_range": "", "speaker_unresolved": false,
    "evidence": [{"chunk_id": "", "quote": ""}], "issues": []
  }],
  "issues": [{"type": "", "message": "", "related": "", "evidence": []}],
  "notes": ""
}

硬约束：
1. 不得输出任何业务 ID；已存在实体只通过名称匹配。
2. 区分「场景资产」与「剧情场次建议」：scenes 是可复用场景资产，episode.scene_beats 是本集剧情分段，不得互相混用。
3. 同一角色使用统一名称；别名放入 aliases。不要因为「沈总/沈知微/总裁」称呼不同就创建多个角色；把证据写入 aliases 或 issues。
4. 换衣服、换发型、妆容变化写入 costume_changes，不得新建角色。
5. 只有推动剧情、被反复使用或需要跨镜头保持一致的道具才进入 props；普通背景物品不要建资产。
6. 对白 speaker 无法确认时 speaker_name 置空、speaker_unresolved=true，不得随机分配。
7. 每条关键候选必须给 evidence.quote，quote 必须是原文中真实存在的短句（≤200 字）。
8. 不虚构音色 ID；voice_description 只写原文有依据的声音特征。
9. 本集标题/摘要/场次建议只是候选，不创建正式场次或镜头。
10. 如果信息不足，写入 issues，不要编造。
"""

_EPISODE_PARSE_PROMPT = PromptTemplate(
    input_variables=[
        "project_name",
        "episode_title",
        "chunk_id",
        "worldbuilding_text",
        "script_text",
        "previous_context",
        "existing_characters_json",
        "existing_scenes_json",
        "existing_props_json",
        "existing_costumes_json",
    ],
    template=(
        "## 项目\n{project_name}\n\n"
        "## 本集\n{episode_title}\n\n"
        "## 当前文本块\nchunk_id={chunk_id}\n\n"
        "## 项目世界观与人物设定\n{worldbuilding_text}\n\n"
        "## 已有角色\n{existing_characters_json}\n\n"
        "## 已有场景\n{existing_scenes_json}\n\n"
        "## 已有道具\n{existing_props_json}\n\n"
        "## 已有服装\n{existing_costumes_json}\n\n"
        "## 前序块已识别实体（用于跨块一致）\n{previous_context}\n\n"
        "## 本集剧本（当前块）\n{script_text}\n\n"
        "## 输出\n"
    ),
)


class EpisodeScriptParserAgent(AgentBase[ScriptParseResult]):
    """单集剧本解析：输出可审核的结构化候选。"""

    agent_key = "episode_script_parse"
    enable_thinking = False

    def _default_system_prompt(self) -> str:
        return _EPISODE_PARSE_SYSTEM_PROMPT

    @property
    def prompt_template(self) -> PromptTemplate:
        return _EPISODE_PARSE_PROMPT

    @property
    def output_model(self) -> type[ScriptParseResult]:
        return ScriptParseResult

    def format_output(self, raw: str) -> ScriptParseResult:
        """容忍常见包裹结构，但拒绝非 JSON 自由文本。"""
        json_str = _extract_json_from_text(raw)
        data: Any = json.loads(json_str)
        if isinstance(data, dict):
            for key in ("ScriptParseResult", "result", "data"):
                inner = data.get(key)
                if isinstance(inner, dict):
                    data = inner
                    break
        if not isinstance(data, dict):
            raise ValueError("剧本解析结果不是 JSON 对象")
        return self.output_model.model_validate(data)

    async def aparse(self, **kwargs: Any) -> ScriptParseResult:
        return await self.aextract(**kwargs)
