"""Skill 加载与 Agent 运行：通用基类与提取类/提示词类 agent。"""

from app.chains.agents.base import AgentBase, STRUCTURED_OUTPUT_METHOD
from app.chains.agents.shot_frame_prompt_agents import (
    ShotFirstFramePromptAgent,
    ShotLastFramePromptAgent,
    ShotKeyFramePromptAgent,
)
from app.chains.agents.script_divider_agent import ScriptDividerAgent
from app.chains.agents.element_extractor_agent import ElementExtractorAgent
from app.chains.agents.entity_merger_agent import EntityMergerAgent
from app.chains.agents.variant_analyzer_agent import VariantAnalyzerAgent
from app.chains.agents.consistency_checker_agent import ConsistencyCheckerAgent
from app.chains.agents.script_optimizer_agent import ScriptOptimizerAgent
from app.chains.agents.script_simplifier_agent import ScriptSimplifierAgent
from app.chains.agents.character_portrait_analysis_agent import CharacterPortraitAnalysisAgent
from app.chains.agents.prop_info_analysis_agent import PropInfoAnalysisAgent
from app.chains.agents.scene_info_analysis_agent import SceneInfoAnalysisAgent
from app.chains.agents.costume_info_analysis_agent import CostumeInfoAnalysisAgent

__all__ = [
    "AgentBase",
    "STRUCTURED_OUTPUT_METHOD",
    "ShotFirstFramePromptAgent",
    "ShotLastFramePromptAgent",
    "ShotKeyFramePromptAgent",
    "ScriptDividerAgent",
    "ElementExtractorAgent",
    "EntityMergerAgent",
    "VariantAnalyzerAgent",
    "ConsistencyCheckerAgent",
    "ScriptOptimizerAgent",
    "ScriptSimplifierAgent",
    "CharacterPortraitAnalysisAgent",
    "PropInfoAnalysisAgent",
    "SceneInfoAnalysisAgent",
    "CostumeInfoAnalysisAgent",
]
