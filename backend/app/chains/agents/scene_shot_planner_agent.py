"""P5：AI 场次内分镜规划 Agent。

只输出结构化镜头候选；不写正式 Shot，不生成参考图/视频。
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import PromptTemplate

from app.chains.agents.base import AgentBase, _extract_json_from_text
from app.schemas.skills.shot_planning import ShotPlanResult

_SYSTEM_PROMPT = """你是短剧分镜导演兼统筹。请把已经确认的剧本、场次结构、角色身份与资产，规划为可制作、可审核的镜头候选。

只输出一个 JSON 对象，不要 markdown 代码块，不要解释。结构：
{
  "shots": [{
    "order": 1,
    "scene_group_index": 1,
    "title": "有画面信息的镜头标题",
    "script_excerpt": "原文短句",
    "source_quote": "原文短句",
    "duration_seconds": 5,
    "camera_shot": "MS",
    "angle": "EYE_LEVEL",
    "movement": "STATIC",
    "action_beats": ["人物/物体的可见动作"],
    "atmosphere": "",
    "visual_description": "主体 + 动作 + 环境 + 光线/构图的完整画面描述",
    "video_prompt_draft": "可直接提交给视频模型的画面描述，不得写旁白或解释",
    "character_names": [],
    "scene_name": null,
    "prop_names": [],
    "costume_name": null,
    "dialogues": [{
      "text": "",
      "speaker_name": null,
      "emotion": "",
      "line_mode": "DIALOGUE",
      "source_dialogue_index": 1
    }],
    "issues": []
  }],
  "coverage_notes": [],
  "notes": ""
}

硬约束（违反任意一条都视为失败，必须修正后重试）：
1. `scene_group_index` 必填，必须对应输入“正式场次”的 1-based 序号；禁止省略、禁止默认成第 1 场。
2. 每一个输入场次至少要有 1 个镜头；场次顺序必须与剧情顺序一致；不得把不同地点的镜头合并到同一场次。
3. `title` 必填且必须描述具体画面/动作，禁止“镜头 1”“场景 1”这类无区分度标题；所有标题不得重复。
4. `visual_description` 必填（至少 10 个字符），必须包含主体、动作、环境；`video_prompt_draft` 必填（至少 10 个字符），必须可直接用于视频生成，不得包含“请生成”“本镜头”等元话语。
5. `action_beats` 至少 1 条，写可见动作，不写心理活动。
6. `source_quote` 必须是当前剧本块中真实存在的短句；`script_excerpt` 与 `source_quote` 至少填一个。
7. 镜头顺序必须与剧情顺序一致；不得增加改变剧情的新事件；不得重复同一画面来凑时长。
8. 保持重要对白、关键事件、地点/时间切换、人物出场退场；无法覆盖时写入 coverage_notes。
9. 对白必须来自输入“已确认对白”：`source_dialogue_index` 填对应 1-based 序号，`speaker_name` 必须与原文说话人一致。
10. 只有人物真正说出口的内容才可用 `line_mode=DIALOGUE`。短信、微信、字幕、屏幕文字必须用 `SCREEN_TEXT`；旁白用 `NARRATION`；不得把短信/屏幕文字当成人物口语，也不得为它们分配说话人。
11. 无法在目标总时长内说完的对白，不得静默删除或改写；可在 coverage_notes 说明“对白需跨镜头/延长时长/人工删减”，并在对应镜头标注。
12. 角色只能使用输入角色正式名称或别名；不得虚构角色；不得因换装创建新角色。
13. `scene_name`/`prop_names`/`costume_name` 使用输入资产名称；无依据时留空。
14. 景别仅限 ECU/CU/MCU/MS/MLS/LS/ELS；角度仅限 EYE_LEVEL/HIGH_ANGLE/LOW_ANGLE/BIRD_EYE/DUTCH/OVER_SHOULDER；运镜仅限 STATIC/PAN/TILT/DOLLY_IN/DOLLY_OUT/TRACK/CRANE/HANDHELD/STEADICAM/ZOOM_IN/ZOOM_OUT。
15. 如果提供“修复反馈”，必须逐条修复反馈中的 blocking 问题，输出完整的新 JSON；不得只输出差异。
"""

_PROMPT = PromptTemplate(
    input_variables=[
        "project_name",
        "chapter_title",
        "target_duration",
        "shot_budget",
        "pace",
        "scene_groups_json",
        "scene_beats_json",
        "characters_json",
        "assets_json",
        "dialogues_json",
        "worldbuilding_text",
        "script_text",
        "previous_context",
        "repair_feedback",
    ],
    template=(
        "## 项目\n{project_name}\n\n"
        "## 剧集\n{chapter_title}\n\n"
        "## 目标总时长（秒）\n{target_duration}\n\n"
        "## 建议镜头数上限（按 5 秒/镜估算）\n{shot_budget}\n\n"
        "## 节奏\n{pace}\n\n"
        "## 正式场次（必须全部覆盖；index 为输出用的 1-based 序号）\n{scene_groups_json}\n\n"
        "## 场次节拍（来自已确认解析）\n{scene_beats_json}\n\n"
        "## 已锁定角色与可用身份/造型版本\n{characters_json}\n\n"
        "## 可用场景/道具/服装资产\n{assets_json}\n\n"
        "## 已确认对白（source_dialogue_index 对应此列表 1-based 序号）\n{dialogues_json}\n\n"
        "## 世界观\n{worldbuilding_text}\n\n"
        "## 前序块已规划镜头\n{previous_context}\n\n"
        "## 当前剧本文本块\n{script_text}\n\n"
        "## 修复反馈（为空表示首次生成；非空时必须逐条修复）\n{repair_feedback}\n\n"
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
