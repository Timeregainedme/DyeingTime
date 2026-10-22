"""图片提示词分块与参考图角色的回归测试。"""

from __future__ import annotations

from app.chains.agents.shot_frame_prompt_agents import (
    _SHOT_FRAME_INPUT_VARS,
    build_frame_prompt_template,
)
from app.chains.prompts import short_drama_rules as rules
from app.schemas.studio.shots import ShotFramePromptMappingRead
from app.services.studio.generation.frame.derive_preview import (
    compose_shot_frame_rendered_prompt,
    replace_reference_names_in_prompt,
)


def _mapping(token: str, kind: str, name: str) -> ShotFramePromptMappingRead:
    return ShotFramePromptMappingRead(
        token=token,
        type=kind,
        id=f"id-{token}",
        name=name,
        file_id=f"file-{token}",
    )


def test_image_reference_role_block_binds_each_token_to_a_job() -> None:
    mappings = [
        _mapping("图1", "character", "林晚"),
        _mapping("图2", "scene", "公寓客厅"),
        _mapping("图3", "prop", "手机"),
    ]
    block = rules.build_image_reference_role_block(mappings, prefix="[参考图角色]")

    assert block.startswith("[参考图角色]")
    assert "图1 为「林晚」的身份与外观参考" in block
    assert "图2 为「公寓客厅」的空间与光照参考" in block
    assert "图3 为「手机」的外观与结构参考" in block


def test_compose_shot_frame_prompt_uses_reference_roles_and_unified_constraints() -> None:
    mappings = [_mapping("图1", "character", "林晚")]
    text = compose_shot_frame_rendered_prompt(
        replaced_prompt="[Scene] 公寓客厅\n[Subject] 图1 站在窗前",
        mappings=mappings,
        negative_prompt="blurry, bad hands",
        avoid_items=["新增无关人物"],
    )

    assert text.startswith("[参考图角色]")
    assert "图1 为「林晚」的身份与外观参考" in text
    assert "[Scene] 公寓客厅" in text
    assert "[统一约束]" in text
    assert "blurry, bad hands" in text
    assert "新增无关人物" in text
    assert "画面内不生成文字" in text


def test_replace_reference_names_keeps_longest_name_first() -> None:
    mappings = [
        _mapping("图1", "character", "林晚"),
        _mapping("图2", "character", "林晚的姐姐"),
    ]
    text = replace_reference_names_in_prompt(
        base_prompt="林晚的姐姐看着林晚。",
        mappings=mappings,
    )
    assert text == "图2看着图1。"


def test_frame_template_uses_block_structure_and_style_pack_variable() -> None:
    template = build_frame_prompt_template("first")

    assert "[Scene]" in template.template
    assert "[Subject]" in template.template
    assert "[Details]" in template.template
    assert "[Constraints]" in template.template
    assert "{style_pack}" in template.template
    assert "{word_budget}" in template.template
    assert "style_pack" in _SHOT_FRAME_INPUT_VARS
    assert "negative_prompt" in _SHOT_FRAME_INPUT_VARS


def test_asset_templates_are_deliverable_first_and_have_reference_block() -> None:
    from scripts.gen_prompt_templates_sql import ASSET_TEMPLATES, ASSET_VARS

    assert "reference_block" in ASSET_VARS
    for category, (_name, _preview, variables, content) in ASSET_TEMPLATES.items():
        assert "reference_block" in variables, category
        assert "[交付物]" in content, category
        assert "[Constraints]" in content, category
        assert "电影级" not in content, category
        assert "8K" not in content, category


def test_asset_other_view_template_has_only_modify_and_preserve() -> None:
    from scripts.gen_prompt_templates_sql import ASSET_TEMPLATES

    for category in (
        "actor_image_other",
        "character_image_other",
        "prop_image_other",
        "scene_image_other",
        "costume_image_other",
    ):
        content = ASSET_TEMPLATES[category][3]
        assert "仅修改" in content, category
        assert "保留" in content, category


def test_image_prompt_length_warning_reports_over_budget() -> None:
    assert rules.image_prompt_length_warning("短提示词") == ""
    warning = rules.image_prompt_length_warning(
        "字" * (rules.IMAGE_PROMPT_LENGTH_RANGE[1] + 1)
    )
    assert "超过建议上限" in warning
