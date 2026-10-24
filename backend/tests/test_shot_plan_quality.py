"""P10-C2：分镜规划结构/质量控制回归测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.studio import SceneGroup
from app.schemas.skills.script_parse import ParsedDialogue
from app.schemas.skills.shot_planning import PlannedShot, ShotPlanResult
from app.services.studio.shot_plan_runner import _plan_precheck


def _shot(*, order: int = 1, scene: int = 1, title: str = "窗前对峙") -> PlannedShot:
    return PlannedShot(
        order=order,
        scene_group_index=scene,
        title=title,
        script_excerpt="沈知微站在窗前。",
        source_quote="沈知微站在窗前。",
        action_beats=["沈知微转身"],
        visual_description="沈知微站在暴雨窗前转身，冷光照亮侧脸。",
        video_prompt_draft="中景，沈知微站在暴雨窗前转身，冷光照亮侧脸。",
    )


def test_planned_shot_rejects_missing_scene_and_content() -> None:
    """缺场次/标题/描述/Prompt 必须触发 Schema 错误，不能静默落默认值。"""
    with pytest.raises(ValidationError):
        PlannedShot(
            order=1,
            title="镜头 1",
            script_excerpt="x",
            action_beats=["a"],
            visual_description="x" * 20,
            video_prompt_draft="x" * 20,
        )
    with pytest.raises(ValidationError):
        PlannedShot(
            order=1,
            scene_group_index=1,
            title="镜头 1",
            script_excerpt="x",
            action_beats=["a"],
            visual_description="短",
            video_prompt_draft="短",
        )


def test_sms_line_mode_is_normalized_to_screen_text() -> None:
    assert ParsedDialogue(text="消息", line_mode="SMS").line_mode == "SCREEN_TEXT"
    assert ParsedDialogue(text="旁白", line_mode="NARRATOR").line_mode == "NARRATION"


def test_plan_precheck_reports_missing_scene_and_duplicate_titles() -> None:
    groups = [
        SceneGroup(id="g1", project_id="p", chapter_id="c", index=1, title="办公室"),
        SceneGroup(id="g2", project_id="p", chapter_id="c", index=2, title="车库"),
    ]
    result = ShotPlanResult(shots=[_shot(title="同一标题"), _shot(order=2, title="同一标题")])
    feedback = _plan_precheck(result, groups)
    joined = " | ".join(feedback)
    assert "车库" in joined
    assert "同一标题" in joined
