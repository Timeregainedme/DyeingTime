"""V2 Mock 纵向验收：P1–P7 项目数据、H3、批量、审核、选择式 MP4 ZIP。""" 

from __future__ import annotations

import asyncio
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.models.studio import (
    AssetImageCandidate,
    AssetVersion,
    Chapter,
    Character,
    CharacterAlias,
    FileItem,
    FileUsage,
    Project,
    ProjectSceneLink,
    ProjectStyle,
    ProjectVisualStyle,
    Scene,
    SceneGroup,
    Shot,
    ShotAssetVersion,
    ShotDetail,
)
from app.models.studio_script_documents import ScriptDocument, ScriptDocumentVersion
from app.models.task import GenerationTask
from app.models.task_links import GenerationTaskLink
from app.schemas.studio.shot_references import GenerationPreviewRead
from app.schemas.studio.timeline import ClipsExportRequest, ClipsExportSelection
from app.schemas.studio.video_batches import VideoBatchCreate
from app.services.studio import shot_references, video_batches
from app.services.studio.generation_quota import get_quota_status
from app.services.studio.shot_references import (
    auto_recommend,
    build_generation_preview,
    build_manifest,
    create_snapshot,
    resolve_prompt_references,
    update_binding,
)
from app.services.studio.shot_video_versions import (
    adopt_shot_video_version_by_task,
    list_shot_video_versions,
    review_shot_video_version,
)
from app.services.studio.timeline import (
    build_selected_clips_archive,
    precheck_clips_export,
)
from app.services.studio.video_batches import create_video_batch, run_video_batch_task
from app.services.studio import timeline as timeline_service


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    evidence: dict[str, object] = {}
    async with maker() as db:
        project = Project(id="p6p", workspace_id="ws-p6", name="P6 短剧", description="", style=ProjectStyle.real_people_city, visual_style=ProjectVisualStyle.live_action)
        chapter = Chapter(id="p6c", project_id=project.id, index=1, title="第1集", raw_text="沈知微看向江屿。")
        character = Character(id="p6char", project_id=project.id, name="沈知微", description="", style=project.style, visual_style=project.visual_style, identity_locked_at=datetime.now(UTC), identity_lock_version=1)
        identity = AssetVersion(id="p6identity", project_id=project.id, asset_type="character", asset_id=character.id, version_no=1, version_kind="identity", variant_type="base", name="身份", status="active")
        character.identity_version_id = identity.id
        scene_group = SceneGroup(id="p6sg", project_id=project.id, chapter_id=chapter.id, index=1, title="办公室", description="", location="办公室", time_of_day="白天", story_event="对白")
        scene_group2 = SceneGroup(id="p6sg2", project_id=project.id, chapter_id=chapter.id, index=2, title="街道", description="", location="街道", time_of_day="夜晚", story_event="转折")
        scene = Scene(id="p6scene", name="办公室", description="", style=project.style, visual_style=project.visual_style)
        scene_version = AssetVersion(id="p6scenev", project_id=project.id, asset_type="scene", asset_id=scene.id, version_no=1, version_kind="base", variant_type="base", name="基础", status="active")
        scene.current_version_id = scene_version.id
        files = [
            FileItem(id="p6-char-file", type="image", name="char", thumbnail="https://mock/char.png", tags=[], storage_key="c"),
            FileItem(id="p6-scene-file", type="image", name="scene", thumbnail="https://mock/scene.png", tags=[], storage_key="s"),
        ]
        script_file = FileItem(id="p6-script-file", type="document", name="第1集.docx", thumbnail="https://mock/script.docx", tags=[], storage_key="scripts/p6.docx")
        script_doc = ScriptDocument(id="p6-script-doc", project_id=project.id, chapter_id=chapter.id, doc_type="episode", title="第1集")
        script_version = ScriptDocumentVersion(id="p6-script-version", document_id=script_doc.id, version_no=1, file_id=script_file.id, file_name="第1集.docx", file_type="docx", content_hash="mock-hash", raw_text="沈知微看向江屿。", text_length=8, status="active", parse_status="parsed")
        script_doc.current_version_id = script_version.id
        script_doc.active_version_id = script_version.id
        db.add_all([
            project, chapter, character, identity, script_file, script_doc, script_version,
            CharacterAlias(character_id=character.id, alias="沈总", normalized_alias="沈总"),
            scene_group, scene_group2, scene, scene_version, *files,
            ProjectSceneLink(project_id=project.id, scene_id=scene.id),
            AssetImageCandidate(project_id=project.id, asset_type="character", asset_id=character.id, asset_version_id=identity.id, candidate_batch_id="b", view_angle="FRONT", source="uploaded", file_id="p6-char-file", status="adopted", is_adopted=True, prompt="", generation_params={}, format="png"),
            AssetImageCandidate(project_id=project.id, asset_type="scene", asset_id=scene.id, asset_version_id=scene_version.id, candidate_batch_id="b", view_angle="FRONT", source="uploaded", file_id="p6-scene-file", status="adopted", is_adopted=True, prompt="", generation_params={}, format="png"),
        ])
        for index in range(1, 13):
            shot_id = f"p6-shot-{index}"
            db.add(Shot(id=shot_id, chapter_id=chapter.id, scene_group_id=(scene_group.id if index <= 6 else scene_group2.id), index=index, title=f"镜头 {index}", script_excerpt="沈知微看向江屿。", status="ready", skip_extraction=True))
            db.add(ShotDetail(id=shot_id, camera_shot="MS", angle="EYE_LEVEL", movement="STATIC", duration=5, video_prompt_draft="@沈总 看向江屿。"))
            db.add(ShotAssetVersion(shot_id=shot_id, asset_type="character", asset_id=character.id, asset_version_id=identity.id, role="character_identity", created_at=datetime.now(UTC)))
            db.add(ShotAssetVersion(shot_id=shot_id, asset_type="scene", asset_id=scene.id, asset_version_id=scene_version.id, role="scene", created_at=datetime.now(UTC)))
        await db.commit()
        evidence["p1_p3"] = {
            "project": project.id,
            "chapter": chapter.id,
            "script_document": script_doc.id,
            "script_version": script_version.id,
            "document_status": script_version.parse_status,
        }

        for index in range(1, 13):
            await auto_recommend(db, shot_id=f"p6-shot-{index}")
        bindings = await shot_references.list_bindings(db, shot_id="p6-shot-1")
        await update_binding(db, binding_id=bindings[0].id, shot_id="p6-shot-1", is_pinned=True)
        await shot_references.reorder_bindings(db, shot_id="p6-shot-1", binding_ids=[bindings[1].id, bindings[0].id])
        refs, manifest, warnings = await build_manifest(db, shot_id="p6-shot-1")
        resolved = await resolve_prompt_references(db, shot_id="p6-shot-1", prompt="@沈总 看向窗外。")
        assert resolved.resolved and resolved.resolved[0].asset_id == character.id
        assert [item.file_id for item in refs] == ["p6-scene-file", "p6-char-file"]

        async def fake_options(_db, *, shot_id, ratio, resolution):
            return type("M", (), {"name": "mock-video", "id": "m"})(), type("P", (), {"provider": "mock", "base_url": None})(), ratio or "9:16", resolution or "768p", 5

        original = shot_references._resolve_options
        shot_references._resolve_options = fake_options
        try:
            previews = 0
            for index in range(1, 13):
                preview_row = await build_generation_preview(
                    db,
                    shot_id=f"p6-shot-{index}",
                    natural_prompt="@沈总 看向窗外。",
                    advanced_prompt="<Picture 1> preserves the scene.",
                    ratio="9:16",
                    resolution="768p",
                )
                if preview_row.blocking_errors:
                    raise AssertionError(preview_row.blocking_errors)
                previews += 1
            preview = await build_generation_preview(db, shot_id="p6-shot-1", natural_prompt="@沈总 看向窗外。", advanced_prompt="<Picture 1> and <Picture 2> preserve the office and character.", ratio="9:16", resolution="768p")
        finally:
            shot_references._resolve_options = original
        snapshot = await create_snapshot(db, shot_id="p6-shot-1", preview=preview, task_id=None, created_by=1)
        await db.flush()
        old_manifest = list(snapshot.manifest)
        # 资产版本更新不改变既有快照。
        scene_version.description = "后来更新"
        await db.flush()
        fresh_bindings = await shot_references.list_bindings(db, shot_id="p6-shot-1")
        evidence["manifest"] = {
            "images": preview.images,
            "order": [item.file_id for item in fresh_bindings if item.is_active],
            "pinned": next(item.is_pinned for item in fresh_bindings if item.id == bindings[0].id),
            "previews": previews,
            "warnings": preview.warnings,
            "prompt_refs": [item.asset_name for item in resolved.resolved],
            "snapshot_manifest_unchanged": snapshot.manifest == old_manifest,
        }

        # 批量：12 镜、并发 4、每镜 1 个候选。Mock 子任务直接成功。
        async def fake_preview(_db, *, shot_id, **kwargs):
            return GenerationPreviewRead(shot_id=shot_id, manifest=[], images=["p6-char-file", "p6-scene-file"], prompt="mock H3 prompt", duration=5, ratio="9:16", input_hash=f"{shot_id}-hash")

        counter = {"n": 0}
        video_payloads: dict[str, bytes] = {}

        async def fake_stage(session, *, shot_id, **kwargs):
            counter["n"] += 1
            task_id = f"p6-video-task-{counter['n']}"
            file_id = f"p6-video-file-{counter['n']}"
            storage_key = f"videos/{file_id}.mp4"
            video_payloads[storage_key] = (Path("tests/fixtures/p7_tiny_red.mp4").read_bytes() if counter["n"] == 1 else Path("tests/fixtures/p7_tiny_blue.mp4").read_bytes())
            session.add(GenerationTask(id=task_id, workspace_id="ws-p6", mode="async_polling", task_kind="video_generation", status="succeeded", progress=100, payload={"run_args": {"input": {"prompt": "mock", "seconds": 5, "ratio": "9:16"}}}))
            session.add(FileItem(id=file_id, type="video", name=file_id, thumbnail=f"https://mock/{file_id}.mp4", tags=[], storage_key=storage_key))
            session.add(GenerationTaskLink(task_id=task_id, resource_type="video", relation_type="video", relation_entity_id=shot_id, file_id=file_id))
            session.add(FileUsage(file_id=file_id, project_id=project.id, chapter_id=chapter.id, shot_id=shot_id, usage_kind="generated_video", source_ref=f"accept:{shot_id}:{file_id}"))
            return task_id, type("S", (), {"id": f"snap-{counter['n']}"})()

        async def fake_file_info(*, key: str):
            data = video_payloads[key]
            return type("I", (), {"size": len(data), "content_type": "video/mp4", "key": key, "url": ""})()

        async def fake_download(*, key: str, byte_range=None):
            data = video_payloads[key]
            if byte_range:
                start, end = byte_range
                return data[start : end + 1]
            return data

        async def fake_to_path(*, key: str, path):
            path.write_bytes(video_payloads[key])

        timeline_service.storage.get_file_info = fake_file_info
        timeline_service.storage.download_file = fake_download
        timeline_service.storage.download_file_to_path = fake_to_path
        video_batches.build_generation_preview = fake_preview
        video_batches.stage_video_from_preview = fake_stage
        video_batches._enqueue = lambda task_id: None
        batch = await create_video_batch(db, chapter=chapter, project=project, body=VideoBatchCreate(shot_ids=[f"p6-shot-{i}" for i in range(1, 13)], candidate_count=1, concurrency=4, allow_low_coverage=True), requested_by=1)
        video_batches.async_session_maker = maker
        await run_video_batch_task(batch.coordinator_task_id or "coord", {"batch_id": batch.id})
        batch = await video_batches.get_batch(db, batch_id=batch.id)
        evidence["batch"] = {"total": batch.total_count, "concurrency": batch.concurrency, "status": batch.status, "succeeded": batch.succeeded_count, "failed": batch.failed_count}

        # 采纳前 6 个镜头，验证部分导出而不是整集等待。
        task_by_shot = {item.shot_id: item.task_id for item in batch.items if item.task_id}
        for index in range(1, 9):
            versions = await list_shot_video_versions(db, shot_id=f"p6-shot-{index}")
            if not versions:
                raise AssertionError(f"镜头 {index} 没有视频候选")
            await adopt_shot_video_version_by_task(
                db, shot_id=f"p6-shot-{index}", task_id=versions[0].task_id
            )
        await db.flush()
        evidence["p4_p6"] = {
            "characters_locked": 1,
            "scene_groups": 2,
            "shots": 12,
            "accepted_videos": 8,
            "batch_items": len(task_by_shot),
        }

        versions = await list_shot_video_versions(db, shot_id="p6-shot-1")
        assert versions and versions[-1].file_id
        chosen = versions[-1]
        await review_shot_video_version(db, shot_id="p6-shot-1", task_id=chosen.task_id, review_status="unsatisfied", issue_tags=["人物脸部漂移"], note="测试标记")
        await adopt_shot_video_version_by_task(db, shot_id="p6-shot-1", task_id=chosen.task_id)
        await db.flush()
        versions = await list_shot_video_versions(db, shot_id="p6-shot-1")
        evidence["review"] = {"candidates": len(versions), "reviewed": next(item.review_status for item in versions if item.task_id == chosen.task_id), "adopted": next(item.is_current for item in versions if item.task_id == chosen.task_id)}

        export_selection = ClipsExportSelection(shot_ids=["p6-shot-1", "p6-shot-2", "p6-shot-7", "p6-shot-8"])
        export_precheck = await precheck_clips_export(
            db, project_id=project.id, selection=export_selection
        )
        if not export_precheck.can_download:
            raise AssertionError(export_precheck.blockers)
        zip_path, zip_name, zip_count, plan_hash = await build_selected_clips_archive(
            db,
            project_id=project.id,
            request=ClipsExportRequest(
                shot_ids=export_selection.shot_ids,
                expected_plan_hash=export_precheck.plan_hash,
            ),
        )
        try:
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                first_bytes = archive.read(names[0])
            evidence["export"] = {
                "zip": zip_name,
                "count": zip_count,
                "names": names,
                "first_is_red_mp4": first_bytes == Path("tests/fixtures/p7_tiny_red.mp4").read_bytes(),
                "plan_hash": plan_hash[:12],
            }
        finally:
            import shutil
            shutil.rmtree(zip_path.parent, ignore_errors=True)

        # 把 shot-1 改成另一个已采纳候选，再导出验证使用新文件、旧文件仍在。
        alt_file_id = "p6-video-alt"
        alt_task_id = "p6-video-alt-task"
        alt_key = "videos/p6-video-alt.mp4"
        video_payloads[alt_key] = Path("tests/fixtures/p7_tiny_blue.mp4").read_bytes()
        db.add(FileItem(id=alt_file_id, type="video", name=alt_file_id, thumbnail="https://mock/alt.mp4", tags=[], storage_key=alt_key))
        db.add(GenerationTask(id=alt_task_id, workspace_id="ws-p6", mode="async_polling", task_kind="video_generation", status="succeeded", progress=100, payload={"run_args": {"input": {"prompt": "mock alt", "seconds": 5, "ratio": "9:16"}}}))
        db.add(GenerationTaskLink(task_id=alt_task_id, resource_type="video", relation_type="video", relation_entity_id="p6-shot-1", file_id=alt_file_id))
        db.add(FileUsage(file_id=alt_file_id, project_id=project.id, chapter_id=chapter.id, shot_id="p6-shot-1", usage_kind="generated_video", source_ref="accept:alt"))
        await db.flush()
        await adopt_shot_video_version_by_task(db, shot_id="p6-shot-1", task_id=alt_task_id)
        await db.flush()
        after = await precheck_clips_export(db, project_id=project.id, selection=ClipsExportSelection(shot_ids=["p6-shot-1"]))
        evidence["export"]["adoption_changed_hash"] = after.plan_hash != plan_hash
        evidence["export"]["old_file_retained"] = await db.get(FileItem, "p6-video-file-1") is not None
        second_zip, _second_name, _second_count, _second_hash = await build_selected_clips_archive(
            db,
            project_id=project.id,
            request=ClipsExportRequest(shot_ids=["p6-shot-1"], expected_plan_hash=after.plan_hash),
        )
        try:
            with zipfile.ZipFile(second_zip) as archive:
                evidence["export"]["new_zip_uses_new_adopted_file"] = (
                    archive.read("E01_SC01_SH001.mp4")
                    == Path("tests/fixtures/p7_tiny_blue.mp4").read_bytes()
                )
        finally:
            import shutil
            shutil.rmtree(second_zip.parent, ignore_errors=True)

        quota = await get_quota_status(db)
        evidence["quota"] = {item["media_type"]: item["remaining"] for item in quota}
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
