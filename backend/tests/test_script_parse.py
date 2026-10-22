"""P3 / C6：解析分块、候选合并、确认落库与差异测试（不调用真实 LLM）。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.bootstrap import bootstrap_all_registries
from app.core.db import Base
from app.models.studio import (
    Chapter,
    Character,
    Costume,
    Project,
    ProjectStyle,
    ProjectVisualStyle,
    Scene,
    ScriptDiffReport,
    ScriptDocument,
    ScriptDocumentVersion,
    ScriptParseCandidate,
    ScriptParseRun,
)
from app.schemas.skills.script_parse import (
    ParsedCharacter,
    ParsedCostumeChange,
    ParsedDialogue,
    ParsedEpisode,
    ParsedProp,
    ParsedScene,
    ParsedSceneBeat,
    ParseEvidence,
    ScriptParseResult,
)
from app.models.task import GenerationTask
from app.services.studio.script_diff import create_diff_report, decide_diff_report
from app.services.studio.script_parse import (
    add_candidate,
    confirm_parse_run,
    delete_candidate,
    merge_candidates,
    update_candidate,
)
from app.services.studio.script_parse_chunking import split_script_for_parse
from app.services.studio.script_parse_runner import (
    ParseMergeAccumulator,
    _normalize_evidence,
    _persist_candidates,
    run_script_parse_task,
)
from app.schemas.studio.script_parse import (
    ScriptParseCandidateCreate,
    ScriptParseCandidateUpdate,
)


@pytest.fixture(autouse=True)
def _bootstrap() -> None:
    bootstrap_all_registries()


async def _build_session() -> tuple[AsyncSession, object]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return session_local(), engine


async def _seed(db: AsyncSession) -> tuple[ScriptDocument, ScriptDocumentVersion, Chapter]:
    project = Project(
        workspace_id="ws-test",
        id="p1",
        name="都市短剧",
        description="",
        style=ProjectStyle.real_people_city,
        visual_style=ProjectVisualStyle.live_action,
    )
    chapter = Chapter(
        id="c1",
        project_id="p1",
        index=1,
        title="第1集：雨夜",
        raw_text="旧正文",
    )
    document = ScriptDocument(
        id="doc1",
        project_id="p1",
        chapter_id="c1",
        doc_type="episode",
        title="第1集剧本",
    )
    version = ScriptDocumentVersion(
        id="ver1",
        document_id="doc1",
        version_no=1,
        file_name="第1集.docx",
        file_type="docx",
        content_hash="hash-1",
        raw_text="# 第1集\n林晚：你回来了。\n沈总：嗯。",
        text_length=20,
        status="active",
        parse_status="completed",
    )
    document.current_version_id = "ver1"
    document.active_version_id = "ver1"
    db.add_all([project, chapter, document, version])
    await db.commit()
    return document, version, chapter


def _candidate(run_id: str, ctype: str, key: str, payload: dict, order: int, status: str = "pending") -> ScriptParseCandidate:
    return ScriptParseCandidate(
        id=str(uuid.uuid4()),
        run_id=run_id,
        candidate_type=ctype,
        candidate_key=key,
        order_index=order,
        payload=payload,
        evidence=[],
        review_status=status,
    )


async def _seed_run(db: AsyncSession) -> ScriptParseRun:
    run = ScriptParseRun(
        id="run1",
        document_id="doc1",
        version_id="ver1",
        status="completed",
        progress=100,
        model_name="mock",
        provider_name="mock",
        chunk_count=1,
    )
    db.add(run)
    db.add_all(
        [
            _candidate("run1", "character", "character:林晚", ParsedCharacter(name="林晚", role="女主", appearance="短发", base_costume="米色风衣").model_dump(), 1),
            _candidate("run1", "character", "character:沈知微", ParsedCharacter(name="沈知微", role="男主", appearance="西装").model_dump(), 2),
            _candidate("run1", "scene", "scene:出租屋", ParsedScene(name="出租屋", location_type="室内").model_dump(), 3),
            _candidate("run1", "prop", "prop:旧相机", ParsedProp(name="旧相机", appearance="银色").model_dump(), 4),
            _candidate("run1", "costume_change", "costume:林晚:灰色卫衣", ParsedCostumeChange(character_name="林晚", base_costume="米色风衣", changed_costume="灰色卫衣").model_dump(), 5),
            _candidate("run1", "scene_beat", "scene_beat:1", ParsedSceneBeat(index=1, title="雨夜归来", location="出租屋").model_dump(), 6),
            _candidate("run1", "episode", "episode:1", ParsedEpisode(title="第1集", summary="林晚回到出租屋。", scene_beats=[ParsedSceneBeat(index=1, title="雨夜归来")]).model_dump(), 7),
            _candidate("run1", "dialogue", "dialogue:1", ParsedDialogue(text="你回来了。", speaker_name="林晚", order=1).model_dump(), 8),
        ]
    )
    await db.commit()
    return run


def test_chunking_covers_text_and_keeps_overlap() -> None:
    text = "\n".join(f"第{i}行：林晚走进房间。" for i in range(1, 200))
    chunks = split_script_for_parse(text, max_chars=500, overlap_lines=3)
    assert len(chunks) > 1
    assert chunks[0].start_char == 0
    assert chunks[-1].end_char == len(text)
    # 相邻块必须有重叠，且块起点持续前进
    for prev, cur in zip(chunks, chunks[1:]):
        assert cur.start_char < prev.end_char
        assert cur.start_char > prev.start_char
    joined = "".join(chunk.text for chunk in chunks)
    assert "第1行：林晚走进房间。" in joined
    assert "第199行：林晚走进房间。" in joined


def test_merge_accumulator_dedupes_characters_and_preserves_dialogue() -> None:
    accumulator = ParseMergeAccumulator(
        existing_characters=[], existing_scenes=[], existing_props=[], existing_costumes=[]
    )
    chunk1 = split_script_for_parse("林晚：你回来了。\n沈总：嗯。")[0]
    chunk2 = split_script_for_parse("沈知微：走吧。\n林晚：好。")[0]
    accumulator.merge_result(
        ScriptParseResult(
            characters=[
                ParsedCharacter(name="林晚", aliases=["小雨"], evidence=[ParseEvidence(quote="林晚")]),
                ParsedCharacter(name="沈知微", aliases=["沈总"], evidence=[ParseEvidence(quote="沈总")]),
            ],
            dialogues=[
                ParsedDialogue(text="你回来了。", speaker_name="林晚", order=1),
                ParsedDialogue(text="嗯。", speaker_name="沈总", order=2),
            ],
            episode=ParsedEpisode(title="第1集", scene_beats=[ParsedSceneBeat(index=1, title="雨夜")]),
        ),
        chunk1,
    )
    accumulator.merge_result(
        ScriptParseResult(
            characters=[ParsedCharacter(name="沈知微", aliases=["沈总"], evidence=[ParseEvidence(quote="沈知微")])],
            dialogues=[ParsedDialogue(text="走吧。", speaker_name="沈知微", order=3)],
        ),
        chunk2,
    )
    result = accumulator.result()
    assert [item.name for item in result.characters].count("沈知微") == 1
    assert any("沈总" in item.aliases for item in result.characters if item.name == "沈知微")
    assert [item.text for item in result.dialogues] == ["你回来了。", "嗯。", "走吧。"]
    assert result.episode.scene_beats


def test_evidence_offsets_are_computed_against_full_text() -> None:
    chunk = split_script_for_parse("第一行\n林晚：你回来了。\n第三行")[0]
    evidence = _normalize_evidence([ParseEvidence(quote="你回来了。")], chunk)
    assert evidence[0].start_char is not None
    assert chunk.text[evidence[0].start_char - chunk.start_char : evidence[0].end_char - chunk.start_char] == "你回来了。"


@pytest.mark.asyncio
async def test_confirm_creates_entities_and_syncs_chapter() -> None:
    db, engine = await _build_session()
    async with db:
        document, version, chapter = await _seed(db)
        run = await _seed_run(db)
        run = (
            await db.execute(
                select(ScriptParseRun)
                .where(ScriptParseRun.id == run.id)
            )
        ).scalars().first()
        assert run is not None
        # selectinload 不是必须：service 会重新读取
        from app.services.studio.script_parse import _load_run

        run = await _load_run(db, "run1")
        for candidate in run.candidates:
            candidate.review_status = "accepted"
        await db.flush()

        confirmed, summary, reused = await confirm_parse_run(db, run=run, confirmed_by=1)
        assert reused is False
        assert confirmed.status == "confirmed"
        assert summary["characters_created"] == 2
        assert summary["scenes_created"] == 1
        assert summary["props_created"] == 1
        assert summary["costumes_created"] >= 2
        assert chapter.raw_text == version.raw_text
        assert confirmed.confirmed_result is not None

        # 幂等：再次确认不会重复创建
        again, summary2, reused2 = await confirm_parse_run(db, run=confirmed, confirmed_by=1)
        assert reused2 is True
        assert summary2 == summary
        characters = (await db.execute(select(Character).where(Character.project_id == "p1"))).scalars().all()
        assert len(characters) == 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_confirm_blocks_pending_and_supports_merge() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        await _seed_run(db)
        from app.services.studio.script_parse import _load_run

        run = await _load_run(db, "run1")
        with pytest.raises(ValueError):
            await confirm_parse_run(db, run=run, confirmed_by=1)

        # 合并两个角色候选后 source 为 merged，target 接受
        char_a = next(item for item in run.candidates if item.candidate_key == "character:林晚")
        char_b = next(item for item in run.candidates if item.candidate_key == "character:沈知微")
        await merge_candidates(
            db,
            run_id="run1",
            source_candidate_id=char_b.id,
            target_candidate_id=char_a.id,
        )
        run = await _load_run(db, "run1")
        for candidate in run.candidates:
            if candidate.review_status == "pending":
                candidate.review_status = "accepted"
        await db.flush()
        confirmed, summary, _ = await confirm_parse_run(db, run=run, confirmed_by=1)
        assert confirmed.status == "confirmed"
        assert summary["characters_created"] == 1
        assert summary["merged"] == 1
        target_payload = next(item.payload for item in confirmed.candidates if item.id == char_a.id)
        assert "沈知微" in target_payload["aliases"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_diff_report_detects_changes_and_impact_without_overwrite() -> None:
    db, engine = await _build_session()
    async with db:
        document, old_version, chapter = await _seed(db)
        db.add(
            Character(
                id="char-lin",
                project_id="p1",
                name="林晚",
                description="女主",
                style=ProjectStyle.real_people_city,
                visual_style=ProjectVisualStyle.live_action,
            )
        )
        await db.commit()
        new_version = ScriptDocumentVersion(
            id="ver2",
            document_id="doc1",
            version_no=2,
            file_name="第1集-v2.md",
            file_type="md",
            content_hash="hash-2",
            raw_text="# 第1集\n林晚穿着灰色卫衣：你回来了。\n沈总：嗯。",
            text_length=30,
            status="candidate",
            parse_status="not_parsed",
        )
        db.add(new_version)
        document.current_version_id = "ver2"
        await db.commit()

        report = await create_diff_report(
            db, document=document, new_version=new_version, created_by=1
        )
        assert report.old_version_id == "ver1"
        assert report.new_version_id == "ver2"
        assert report.text_diff
        assert "林晚" in report.impact["assets"]["characters"]
        assert report.impact["shots"] == []
        # 正式章节正文不被 diff 自动修改
        assert chapter.raw_text == "旧正文"

        decided = await decide_diff_report(
            db,
            report=report,
            status_value="accepted",
            decisions={"accept_change": True},
            decided_by=1,
        )
        assert decided.status == "accepted"
        assert decided.decisions["accept_change"] is True
        assert chapter.raw_text == "旧正文"
    await engine.dispose()


@pytest.mark.asyncio
async def test_update_candidate_marks_edited_and_ignored() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        await _seed_run(db)
        from app.services.studio.script_parse import _load_run

        run = await _load_run(db, "run1")
        candidate = next(item for item in run.candidates if item.candidate_type == "character")
        updated = await update_candidate(
            db,
            run_id="run1",
            candidate_id=candidate.id,
            body=ScriptParseCandidateUpdate(payload={**candidate.payload, "role": "女主（修订）"}),
        )
        assert updated.review_status == "edited"
        assert updated.payload["role"] == "女主（修订）"

        ignored = await update_candidate(
            db,
            run_id="run1",
            candidate_id=candidate.id,
            body=ScriptParseCandidateUpdate(review_status="ignored"),
        )
        assert ignored.review_status == "ignored"
    await engine.dispose()


@pytest.mark.asyncio
async def test_runner_persists_candidates_with_mock_agent(monkeypatch) -> None:
    # runner 使用全局 async_session_maker；测试必须把它重绑到独立内存库。
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with maker() as db:
        await _seed(db)
        db.add(
            GenerationTask(
                id="task-parse",
                workspace_id="ws-test",
                mode="async_polling",
                task_kind="script_parse",
                status="pending",
                progress=0,
                payload={},
            )
        )
        db.add(
            ScriptParseRun(
                id="run-runner",
                document_id="doc1",
                version_id="ver1",
                task_id="task-parse",
                status="pending",
                progress=0,
                model_id="m-text",
                chunk_count=1,
                input_hash="hash",
            )
        )
        await db.commit()

    async def _fake_build(_db, *, model_id=None, thinking=False):
        return (
            object(),
            type("M", (), {"id": "m-text", "name": "mock-model"})(),
            type("P", (), {"name": "mock-provider"})(),
        )

    async def _fake_parse(self, **kwargs):
        return ScriptParseResult(
            characters=[ParsedCharacter(name="林晚", role="女主", base_costume="米色风衣")],
            scenes=[ParsedScene(name="出租屋", location_type="室内")],
            props=[ParsedProp(name="旧相机", appearance="银色")],
            costume_changes=[ParsedCostumeChange(character_name="林晚", changed_costume="灰色卫衣")],
            episode=ParsedEpisode(
                title="第1集",
                summary="林晚归来。",
                scene_beats=[ParsedSceneBeat(index=1, title="雨夜归来", location="出租屋")],
            ),
            dialogues=[ParsedDialogue(text="你回来了。", speaker_name="林晚")],
        )

    monkeypatch.setattr("app.services.studio.script_parse_runner.async_session_maker", maker)
    monkeypatch.setattr("app.services.studio.script_parse_runner.build_text_llm", _fake_build)
    monkeypatch.setattr("app.services.studio.script_parse_runner.EpisodeScriptParserAgent.aparse", _fake_parse)

    await run_script_parse_task("task-parse", {"run_id": "run-runner"})

    async with maker() as db:
        from app.services.studio.script_parse import _load_run

        run = await _load_run(db, "run-runner")
        assert run.status == "completed"
        assert run.chunk_count == 1
        types = {item.candidate_type for item in run.candidates}
        assert {"character", "scene", "prop", "costume_change", "scene_beat", "episode", "dialogue"} <= types
        task = await db.get(GenerationTask, "task-parse")
        assert task is not None
        assert str(task.status) in {"succeeded", "GenerationTaskStatus.succeeded"}
    await engine.dispose()


@pytest.mark.asyncio
async def test_confirm_honors_manual_match_and_can_clear_it() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        existing_scene = Scene(
            id="scene-existing",
            name="已有场景",
            description="人工确认的场景",
            style=ProjectStyle.real_people_city,
            visual_style=ProjectVisualStyle.live_action,
        )
        db.add(existing_scene)
        run = ScriptParseRun(
            id="run-match",
            document_id="doc1",
            version_id="ver1",
            status="completed",
            progress=100,
            model_name="mock",
            provider_name="mock",
            chunk_count=1,
        )
        candidate = _candidate(
            "run-match",
            "scene",
            "scene:新场景名",
            ParsedScene(name="新场景名", location_type="室内").model_dump(),
            1,
        )
        candidate.matched_entity_id = "scene-existing"
        db.add_all([run, candidate])
        await db.commit()

        from app.services.studio.script_parse import _load_run

        loaded = await _load_run(db, "run-match")
        updated = await update_candidate(
            db,
            run_id="run-match",
            candidate_id=loaded.candidates[0].id,
            body=ScriptParseCandidateUpdate(matched_entity_id=None),
        )
        assert updated.matched_entity_id is None

        await update_candidate(
            db,
            run_id="run-match",
            candidate_id=loaded.candidates[0].id,
            body=ScriptParseCandidateUpdate(
                review_status="accepted", matched_entity_id="scene-existing"
            ),
        )
        loaded = await _load_run(db, "run-match")
        confirmed, summary, _ = await confirm_parse_run(db, run=loaded, confirmed_by=1)
        assert confirmed.status == "confirmed"
        assert summary["scenes_linked"] == 1
        assert summary["scenes_created"] == 0
        scenes = (await db.execute(select(Scene))).scalars().all()
        assert len(scenes) == 1
        assert scenes[0].name == "已有场景"
    await engine.dispose()


@pytest.mark.asyncio
async def test_add_and_delete_manual_candidate() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        await _seed_run(db)
        created = await add_candidate(
            db,
            run_id="run1",
            body=ScriptParseCandidateCreate(
                candidate_type="character",
                payload=ParsedCharacter(name="新角色", role="配角").model_dump(),
            ),
        )
        assert created.review_status == "edited"
        assert created.candidate_key.startswith("manual:")

        run = await delete_candidate(db, run_id="run1", candidate_id=created.id)
        assert all(item.id != created.id for item in run.candidates)
    await engine.dispose()


@pytest.mark.asyncio
async def test_repersist_preserves_manual_edit() -> None:
    db, engine = await _build_session()
    async with db:
        await _seed(db)
        run = ScriptParseRun(
            id="run-repersist",
            document_id="doc1",
            version_id="ver1",
            status="running",
            progress=10,
        )
        db.add(run)
        await db.commit()

        result = ScriptParseResult(
            characters=[ParsedCharacter(name="林晚", role="AI 原始设定")]
        )
        await _persist_candidates(db, run=run, result=result)
        from app.services.studio.script_parse import _load_run

        loaded = await _load_run(db, "run-repersist")
        candidate = loaded.candidates[0]
        await update_candidate(
            db,
            run_id=run.id,
            candidate_id=candidate.id,
            body=ScriptParseCandidateUpdate(
                payload={**candidate.payload, "role": "人工修订"}
            ),
        )
        # 模拟同一 run 的任务重试再次持久化；人工修改不能被覆盖。
        await _persist_candidates(db, run=run, result=result)
        loaded = await _load_run(db, "run-repersist")
        assert len(loaded.candidates) == 2
        character = next(
            item for item in loaded.candidates if item.candidate_type == "character"
        )
        assert character.payload["role"] == "人工修订"
    await engine.dispose()
