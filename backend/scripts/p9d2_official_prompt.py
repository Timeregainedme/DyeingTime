"""P9-D2：按官方 h3-prompt-writing Skill 生成 Ref2VA 英文正文。

该脚本只读取本地测试镜头 `s-p9d2-continuity` 的 IR，不写数据库、不调用供应商。
输出可作为高级 Prompt 提交；提交前仍必须走 `generation-preview` 做 manifest /
input_hash 校验。
"""

from __future__ import annotations

import asyncio

from app.chains.prompts.ir import IRDialogueInput, build_video_prompt_ir
from app.chains.prompts.renderers.h3 import H3Prose, render_h3_reference
from app.core.db import async_session_maker
from app.services.studio.shot_references import build_manifest
from app.services.studio.shot_video_prompt_pack import build_shot_video_prompt_pack

SHOT_ID = "s-p9d2-continuity"
NATURAL_PROMPT = (
    "@顾言 与 @沈知微 在办公室内相对而立，顾言开口解释，沈知微保持沉默。"
)


def _prose() -> H3Prose:
    return H3Prose(
        subject_definitions=(
            "<Subject 1> is the adult male character 顾言 in <Picture 1>, with short dark hair, "
            "a dark grey sweater, and a light blue collared shirt.\n"
            "<Subject 2> is the adult female character 沈知微 in <Picture 2>, with long dark "
            "wavy hair and a deep red long-sleeve top.\n"
            "<Subject 3> is the modern office environment in <Picture 3>, with black-framed "
            "glass partitions on both sides, a long grey corridor, a cream sofa, a yellow chair, "
            "a floor lamp, and warm pendant lights."
        ),
        summary=(
            "[reference generation] The target video shows <Subject 1> and <Subject 2> facing "
            "each other in <Subject 3> in one continuous medium shot. <Subject 1> speaks one "
            "line while <Subject 2> remains silent and reacts."
        ),
        retention_analysis=(
            "<Subject 1> (appears in [Shot 1]): fully_preserved - his identity, short dark hair, "
            "dark grey sweater, and light blue collared shirt are retained from <Picture 1>.\n"
            "<Subject 2> (appears in [Shot 1]): fully_preserved - her identity, long dark wavy "
            "hair, and deep red top are retained from <Picture 2>.\n"
            "<Subject 3> (appears in [Shot 1]): fully_preserved - the glass partitions, corridor "
            "depth, cream sofa, yellow chair, floor lamp, and warm pendant lights are retained "
            "from <Picture 3>."
        ),
        detailed_description=(
            "The target video uses a realistic live-action short-drama look with cool daylight "
            "from the glass partitions and warm practical lamps.\n"
            "[Shot 1] A medium two-shot frames <Subject 1> on the left and <Subject 2> on the "
            "right inside <Subject 3>. The camera pushes in with small amplitude at slow speed "
            "while keeping both characters and the office background in the same continuous "
            "space. <Subject 1> (S1), using this voice profile: Young adult male voice, clear "
            "timbre, moderate pace, restrained emotion, holds his ground and says, "
            "<d>[Chinese] 你听我解释。</d> <Subject 2> stays silent, "
            "keeps her lips closed, and shifts her gaze toward him without leaving her position. "
            "The glass partitions, corridor depth, cream sofa, floor lamp, and warm pendant "
            "lights remain fixed behind them throughout the shot; the camera does not cut to "
            "another room or change the background."
        ),
        overall_soundscape=(
            "Quiet office room tone with a low ventilation hum and faint distant footsteps. "
            "Fabric movement is audible as the man shifts his weight."
        ),
        non_diegetic_music="N/A",
    )


async def main() -> None:
    async with async_session_maker() as db:
        pack = await build_shot_video_prompt_pack(db, shot_id=SHOT_ID)
        refs, _manifest, _warnings = await build_manifest(db, shot_id=SHOT_ID)
        dialogues = [
            IRDialogueInput(
                speaker_character_id=item.speaker_character_id or "",
                speaker_name=item.speaker_name,
                voice_description=item.voice_description,
                text=item.text,
                emotion=item.emotion,
                line_mode=item.line_mode,
            )
            for item in pack.dialogues
        ]
        ir = build_video_prompt_ir(
            pack,
            dialogues=dialogues,
            reference_mode="reference",
            duration_seconds=pack.camera.duration or 5,
            aspect_ratio="9:16",
            references_override=refs,
            natural_prompt=NATURAL_PROMPT,
        )
        result = render_h3_reference(ir, prose=_prose())
        print(result.text)
        print("\n--- warnings ---", result.warnings)
        print("--- refs ---", [(r.token, r.kind, r.name, r.ref_id) for r in ir.references])
        print("--- subjects ---", [(s.label, s.kind, s.name, s.source_tokens) for s in ir.subjects])
        print("--- speakers ---", [(d.speaker_id, d.speaker_name, d.speaker_character_id, d.text) for d in ir.shots[0].dialogues])


if __name__ == "__main__":
    asyncio.run(main())
