"""分镜分块与合并的纯函数测试。"""

from __future__ import annotations

from app.schemas.skills.script_processing import ScriptDivisionResult, ShotDivision
from app.services.studio.script_division_chunking import (
    ScriptChunk,
    merge_chunk_shots,
    split_script_for_division,
)


def _shot(index: int, excerpt: str, name: str = "") -> ShotDivision:
    return ShotDivision(index=index, script_excerpt=excerpt, shot_name=name)


def test_split_by_timestamp_markers() -> None:
    text = "\n".join(
        [
            "**[00:00–00:04]**",
            "深夜值班室，护工看表。",
            "",
            "**[00:04–00:07]**",
            "护工走到老人房门口。",
            "",
            "**[00:07–00:10]**",
            "纸尿裤特写。",
        ]
    )
    chunks = split_script_for_division(text, max_chars=1000, min_chars=1)

    assert len(chunks) == 3
    assert chunks[0].text.startswith("**[00:00–00:04]**")
    assert chunks[1].text.startswith("**[00:04–00:07]**")
    assert chunks[2].text.startswith("**[00:07–00:10]**")


def test_split_without_markers_uses_line_budget() -> None:
    text = "\n".join(f"第{i}行：角色推门进入房间。" for i in range(1, 41))
    chunks = split_script_for_division(text, max_chars=10_000, max_lines=10, min_chars=1)

    assert len(chunks) >= 4
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == 40


def test_merge_drops_boundary_duplicate_and_reindexes() -> None:
    first = ScriptDivisionResult(
        shots=[
            _shot(1, "护工在值班室抬手看表。", "看表"),
            _shot(2, "她起身走向老人房门口。", "起身"),
        ],
        total_shots=2,
    )
    second = ScriptDivisionResult(
        shots=[
            _shot(1, "她起身走向老人房门口。", "起身"),
            _shot(2, "她推门进入房间，手电照向床铺。", "探视"),
        ],
        total_shots=2,
    )
    merged = merge_chunk_shots(
        [
            (ScriptChunk(index=0, text="a", start_line=1, end_line=2), first),
            (ScriptChunk(index=1, text="b", start_line=3, end_line=4), second),
        ]
    )

    assert [shot.script_excerpt for shot in merged.shots] == [
        "护工在值班室抬手看表。",
        "她起身走向老人房门口。",
        "她推门进入房间，手电照向床铺。",
    ]
    assert [shot.index for shot in merged.shots] == [1, 2, 3]
    assert merged.total_shots == 3


def test_merge_skips_empty_excerpt() -> None:
    result = ScriptDivisionResult(
        shots=[_shot(1, "  "), _shot(2, "有效画面")],
        total_shots=2,
    )
    merged = merge_chunk_shots(
        [(ScriptChunk(index=0, text="a", start_line=1, end_line=1), result)]
    )
    assert [shot.script_excerpt for shot in merged.shots] == ["有效画面"]
    assert merged.shots[0].index == 1
