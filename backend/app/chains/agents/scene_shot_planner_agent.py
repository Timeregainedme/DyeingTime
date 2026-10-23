"""P5：AI 场次内分镜规划 Agent。

只输出结构化镜头候选；不写正式 Shot，不生成参考图/视频。
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import PromptTemplate

from app.chains.agents.base import AgentBase, _extract_json_from_text
from app.schemas.skills.shot_planning import ShotPlanResult

_SYSTEM_PROMPT = """\
你是短剧分镜导演兼统筹。请把已经确认的剧本、场次结构、角色身份与资产，规划为可制作的镜头候选。

只输出一个 JSON 对象，不要 markdown 代码块，不要解释。结构：
{
  "shots": [{
    "order": 1,
    "scene_group_index": 1,
    "title": "",
    "script_excerpt": "",
    "source_quote": "",
    "duration_seconds": 5,
    "camera_shot": "MS",
    "angle": "EYE_LEVEL",
    "movement": "STATIC",
    "action_beats": [],
    "atmosphere": "",
    "visual_description": "",
    "video_prompt_draft": "",
    "character_names": [],
    "scene_name": null,
    "prop_names": [],
    "costume_name": null,
    "dialogues": [{"text": "", "speaker_name": null, "emotion": "", "line_mode": "DIALOGUE"}],
    "issues": []
  }],
  "coverage_notes": [],
  "notes": ""
}

硬约束：
1. 镜头顺序必须与剧情顺序一致；不得增加改变剧情的新事件。
2. 每条镜头必须能追溯到原文；script_excerpt/source_quote 使用原文短句，不编造。
3. 单镜头时长必须在项目业务范围内；对白太长或动作复杂时拆成多个镜头，不能硬塞。
4. 保持重要对白、关键事件、地点/时间切换、人物出场退场；无法覆盖时写入 coverage_notes。
5. scene_group_index 必须对应输入场次列表的 1-based 序号。
6. character_names 使用输入角色正式名称或别名；不要虚构角色，不要因换装创建新角色。
7. scene_name/prop_names/costume_name 使用输入资产名称；没有依据时留空。
8. 对白 speaker 不明确时 speaker_name 置空，并写入 issues；不得随机分配。
9. 不使用运镜/景别代码之外的自由文本；景别 ECU/CU/MCU/MS/MLS/LS/ELS，角度 EYE_LEVEL/HIGH_ANGLE/LOW_ANGLE/BIRD_EYE/DUTCH/OVER_SHOULDER，运镜 STATIC/PAN/TILT/DOLLY_IN/DOLLY_OUT/TRACK/CRANE/HANDHELD/STEADICAM/ZOOM_IN/ZOOM_OUT。
10. 长文本分块时，当前块只输出块内内容；保持跨块人物/场景一致，不重复已输出的镜头。
"""

_PROMPT = PromptTemplate(
    input_variables=[
        "project_name",
        "chapter_title",
        "target_duration",
        "pace",
        "scene_groups_json",
        "characters_json",
        "assets_json",
        "worldbuilding_text",
        "script_text",
        "previous_context",
    ],
    template=(
        "## 项目\n{project_name}\n\n"
        "## 剧集\n{chapter_title}\n\n"
        "## 目标总时长（秒）\n{target_duration}\n\n"
        "## 节奏\n{pace}\n\n"
        "## 正式场次（1-based 顺序）\n{scene_groups_json}\n\n"
        "## 已锁定角色与可用身份/造型版本\n{characters_json}\n\n"
        "## 可用场景/道具/服装资产\n{assets_json}\n\n"
        "## 世界观\n{worldbuilding_text}\n\n"
        "## 前序块已规划镜头\n{previous_context}\n\n"
        "## 当前剧本文本块\n{script_text}\n\n"
        "## 输出\n"
    ),
)


class SceneShotPlannerAgent(AgentBase[ShotPlanResult]):
    """单集分镜规划：输出可审核的结构化镜头候选。"""

    agent_key = "episode_shot_plan"
    enable_thinking = False

    def _default_system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    @property
    def prompt_template(self) -> PromptTemplate:
        return _PROMPT

    @property
    def output_model(self) -> type[ShotPlanResult]:
        return ShotPlanResult

    def format_output(self, raw: str) -> ShotPlanResult:
        data: Any = json.loads(_extract_json_from_text(raw))
        if isinstance(data, dict):
            for key in ("ShotPlanResult", "result", "data"):
                if isinstance(data.get(key), dict):
                    data = data[key]
                    break
        if not isinstance(data, dict):
            raise ValueError("分镜规划结果不是 JSON 对象")
        return self.output_model.model_validate(data)

    async def aplan(self, **kwargs: Any) -> ShotPlanResult:
        return await self.aextract(**kwargs)


__all__ = ["SceneShotPlannerAgent"]
