"""P7 / C15：选择式 MP4 ZIP 导出、预检查与版本一致性测试。"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.core.storage import StoredFileInfo
from app.models.studio import (
    Chapter,
    FileItem,
    FileUsage,
    Project,
    ProjectStyle,
    ProjectVisualStyle,
    SceneGroup,
    Shot,
    ShotDetail,
)
from app.schemas.studio.timeline import ClipsExportRequest, ClipsExportSelection
from app.services.studio import timeline
from app.services.studio.timeline import (
    ClipsExportConflict,
    build_selected_clips_archive,
    precheck_clips_export,
)

_FIXTURES = Path(__file__).parent / "fixtures"
MP4_A = (_FIXTURES / "p7_tiny_red.mp4").read_bytes()
MP4_B = (_FIXTURES / "p7_tiny_blue.mp4").read_bytes()
MP4_C = MP4_A
MP4_D = MP4_B
MOV = b"\x00\x00\x00\x14ftypqt  " + b"M" * 64
PAYLOADS = {
    "p7-f1": MP4_A,
    "p7-f2": MP4_B,
    "p7-f4": MP4_C,
    "p7-f6": MP4_D,
    "p7-f1b": MP4_B,
    "p7-f7": MP4_A,
}


async def _build():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return maker, engine


async def _seed(db: AsyncSession) -> None:
    project = Project(
        id="p7-project",
        workspace_id="ws-p7",
        name="都市测试项目",
        description="",
        style=ProjectStyle.real_people_city,
        visual_style=ProjectVisualStyle.live_action,
    )
    chapter = Chapter(id="p7-ch", project_id=project.id, index=1, title="第1集", raw_text="")
    g1 = SceneGroup(
        id="p7-g1", project_id=project.id, chapter_id=chapter.id, index=1,
        title="第一场", description="", location="办公室", time_of_day="白天", story_event="",
    )
    g2 = SceneGroup(
        id="p7-g2", project_id=project.id, chapter_id=chapter.id, index=2,
        title="第二场", description="", location="街道", time_of_day="夜晚", story_event="",
    )
    db.add_all([project, chapter, g1, g2])
    shots = [
        ("p7-s1", 1, g1.id, "p7-f1", 5, "accept"),
        ("p7-s2", 2, g1.id, "p7-f2", 6, "accept"),
        ("p7-s3", 3, g2.id, None, 4, "missing"),
        ("p7-s4", 4, None, "p7-f4", 7, "accept"),
        ("p7-s5", 5, g2.id, "p7-f5", 3, "mov"),
        ("p7-s6", 6, g2.id, "p7-f6", 5, "accept"),
    ]
    for shot_id, index, scene_id, file_id, duration, _kind in shots:
        db.add(
            Shot(
                id=shot_id,
                chapter_id=chapter.id,
                scene_group_id=scene_id,
                index=index,
                title=f"镜头 {index}",
                status="ready",
                generated_video_file_id=file_id,
            )
        )
        db.add(
            ShotDetail(
                id=shot_id,
                camera_shot="MS",
                angle="EYE_LEVEL",
                movement="STATIC",
                duration=duration,
            )
        )
    file_rows = [
        ("p7-f1", "videos/f1.mp4"),
        ("p7-f2", "videos/f2.mp4"),
        ("p7-f4", "videos/f4.mp4"),
        ("p7-f5", "videos/f5.mov"),
        ("p7-f6", "videos/f6.mp4"),
        ("p7-f1b", "videos/f1b.mp4"),
    ]
    db.add_all(
        [
            FileItem(
                id=file_id,
                type="video",
                name=file_id,
                thumbnail=f"https://mock/{file_id}",
                tags=[],
                storage_key=key,
            )
            for file_id, key in file_rows
        ]
    )
    await db.flush()
    db.add_all(
        [
            FileUsage(
                file_id=file_id,
                project_id=project.id,
                chapter_id=chapter.id,
                shot_id=shot_id,
                usage_kind="generated_video",
                source_ref=f"test:{shot_id}",
            )
            for shot_id, file_id in [
                ("p7-s1", "p7-f1"),
                ("p7-s2", "p7-f2"),
                ("p7-s4", "p7-f4"),
                ("p7-s5", "p7-f5"),
                ("p7-s6", "p7-f6"),
                ("p7-s1", "p7-f1b"),
            ]
        ]
    )
    await db.commit()


@pytest.fixture(autouse=True)
def _storage(monkeypatch):
    async def _get_info(*, key: str):
        file_id = {
            "videos/f1.mp4": "p7-f1",
            "videos/f2.mp4": "p7-f2",
            "videos/f4.mp4": "p7-f4",
            "videos/f5.mov": "p7-f5",
            "videos/f6.mp4": "p7-f6",
            "videos/f1b.mp4": "p7-f1b",
            "videos/f7.mp4": "p7-f7",
        }.get(key)
        if file_id is None:
            raise FileNotFoundError(key)
        data = PAYLOADS[file_id]
        return StoredFileInfo(
            key=key, url="", size=len(data), content_type="video/mp4" if key.endswith(".mp4") else "video/quicktime"
        )

    async def _download(*, key: str, byte_range=None):
        file_id = {
            "videos/f1.mp4": "p7-f1",
            "videos/f2.mp4": "p7-f2",
            "videos/f4.mp4": "p7-f4",
            "videos/f5.mov": "p7-f5",
            "videos/f6.mp4": "p7-f6",
            "videos/f1b.mp4": "p7-f1b",
            "videos/f7.mp4": "p7-f7",
        }[key]
        data = PAYLOADS[file_id]
        if byte_range:
            start, end = byte_range
            return data[start : end + 1]
        return data

    async def _to_path(*, key: str, path):
        file_id = {
            "videos/f1.mp4": "p7-f1",
            "videos/f2.mp4": "p7-f2",
            "videos/f4.mp4": "p7-f4",
            "videos/f5.mov": "p7-f5",
            "videos/f6.mp4": "p7-f6",
            "videos/f1b.mp4": "p7-f1b",
            "videos/f7.mp4": "p7-f7",
        }[key]
        path.write_bytes(PAYLOADS[file_id])

    monkeypatch.setattr(timeline.storage, "get_file_info", _get_info)
    monkeypatch.setattr(timeline.storage, "download_file", _download)
    monkeypatch.setattr(timeline.storage, "download_file_to_path", _to_path)


@pytest.mark.asyncio
async def test_precheck_names_order_and_issues() -> None:
    maker, engine = await _build()
    async with maker() as db:
        await _seed(db)
        result = await precheck_clips_export(
            db, project_id="p7-project", selection=ClipsExportSelection(include_all=True)
        )
        assert result.selected_count == 6
        assert result.exportable_count == 4
        assert result.no_accepted_count == 1
        assert result.unsupported_count == 1
        assert result.can_download is False
        assert [item.shot_id for item in result.items] == [
            "p7-s1", "p7-s2", "p7-s3", "p7-s4", "p7-s5", "p7-s6"
        ]
        assert [item.file_name for item in result.items] == [
            "E01_SC01_SH001.mp4",
            "E01_SC01_SH002.mp4",
            "E01_SC02_SH003.mp4",
            "E01_SC00_SH004.mp4",
            "E01_SC02_SH005.mp4",
            "E01_SC02_SH006.mp4",
        ]
        assert result.total_duration == 30
        assert any("E01_SC02_SH003.mp4" in blocker and "尚未采纳" in blocker for blocker in result.blockers)
        assert any("E01_SC02_SH005.mp4" in blocker and "MP4" in blocker for blocker in result.blockers)
    await engine.dispose()


@pytest.mark.asyncio
async def test_zip_only_selected_mp4_and_stable_order() -> None:
    maker, engine = await _build()
    async with maker() as db:
        await _seed(db)
        selection = ClipsExportRequest(shot_ids=["p7-s4", "p7-s1", "p7-s2", "p7-s6"])
        precheck = await precheck_clips_export(db, project_id="p7-project", selection=selection)
        assert precheck.can_download
        path, filename, count, plan_hash = await build_selected_clips_archive(
            db, project_id="p7-project", request=selection.model_copy(update={"expected_plan_hash": precheck.plan_hash})
        )
        try:
            assert count == 4
            assert filename.startswith("DyeingTime_")
            assert filename.endswith(".zip")
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                assert names == [
                    "E01_SC01_SH001.mp4",
                    "E01_SC01_SH002.mp4",
                    "E01_SC00_SH004.mp4",
                    "E01_SC02_SH006.mp4",
                ]
                assert not any(name.endswith(".txt") for name in names)
                assert archive.read("E01_SC01_SH001.mp4") == MP4_A
                assert archive.read("E01_SC01_SH002.mp4") == MP4_B
            # 输入顺序不影响输出顺序。
            again = await precheck_clips_export(
                db,
                project_id="p7-project",
                selection=ClipsExportSelection(shot_ids=["p7-s6", "p7-s2", "p7-s4", "p7-s1"]),
            )
            assert again.plan_hash == precheck.plan_hash
        finally:
            import shutil
            shutil.rmtree(path.parent, ignore_errors=True)
    await engine.dispose()


@pytest.mark.asyncio
async def test_plan_hash_detects_adoption_change() -> None:
    maker, engine = await _build()
    async with maker() as db:
        await _seed(db)
        selection = ClipsExportSelection(shot_ids=["p7-s1"])
        before = await precheck_clips_export(db, project_id="p7-project", selection=selection)
        shot = await db.get(Shot, "p7-s1")
        assert shot is not None
        shot.generated_video_file_id = "p7-f1b"
        await db.commit()
        with pytest.raises(ClipsExportConflict):
            await build_selected_clips_archive(
                db,
                project_id="p7-project",
                request=ClipsExportRequest(shot_ids=["p7-s1"], expected_plan_hash=before.plan_hash),
            )
        after = await precheck_clips_export(db, project_id="p7-project", selection=selection)
        assert after.plan_hash != before.plan_hash
        assert after.items[0].file_id == "p7-f1b"
        # 旧文件仍存在，新导出使用新采纳文件。
        assert await db.get(FileItem, "p7-f1") is not None
    await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_and_cross_project_shot_are_rejected() -> None:
    maker, engine = await _build()
    async with maker() as db:
        await _seed(db)
        with pytest.raises(ValueError, match="重复"):
            await precheck_clips_export(
                db,
                project_id="p7-project",
                selection=ClipsExportSelection(shot_ids=["p7-s1", "p7-s1"]),
            )
        with pytest.raises(ValueError, match="不属于当前项目"):
            await precheck_clips_export(
                db,
                project_id="p7-project",
                selection=ClipsExportSelection(shot_ids=["other-shot"]),
            )
        with pytest.raises(ValueError, match="选择不能为空"):
            await precheck_clips_export(
                db,
                project_id="p7-project",
                selection=ClipsExportSelection(shot_ids=[]),
            )
    await engine.dispose()


@pytest.mark.asyncio
async def test_storage_missing_and_unowned_file_are_blocked() -> None:
    from sqlalchemy import delete

    maker, engine = await _build()
    async with maker() as db:
        await _seed(db)
        file_item = await db.get(FileItem, "p7-f1")
        assert file_item is not None
        file_item.storage_key = "videos/missing.mp4"
        await db.execute(delete(FileUsage).where(FileUsage.file_id == "p7-f2"))
        await db.commit()
        result = await precheck_clips_export(
            db, project_id="p7-project", selection=ClipsExportSelection(include_all=True)
        )
        by_shot = {item.shot_id: item for item in result.items}
        assert by_shot["p7-s1"].status == "storage_unavailable"
        assert by_shot["p7-s2"].status == "file_missing"
        assert "不属于当前项目" in by_shot["p7-s2"].error
        assert result.can_download is False
    await engine.dispose()


@pytest.mark.asyncio
async def test_chapter_and_scene_selection_and_cross_chapter_export() -> None:
    maker, engine = await _build()
    async with maker() as db:
        await _seed(db)
        chapter2 = Chapter(id="p7-ch2", project_id="p7-project", index=2, title="第2集", raw_text="")
        scene3 = SceneGroup(
            id="p7-g3", project_id="p7-project", chapter_id=chapter2.id, index=1,
            title="第二集第一场", description="", location="天台", time_of_day="清晨", story_event="",
        )
        shot7 = Shot(id="p7-s7", chapter_id=chapter2.id, scene_group_id=scene3.id, index=1, title="跨集镜头", status="ready", generated_video_file_id="p7-f7")
        db.add_all([
            chapter2, scene3, shot7,
            ShotDetail(id="p7-s7", camera_shot="MS", angle="EYE_LEVEL", movement="STATIC", duration=4),
            FileItem(id="p7-f7", type="video", name="f7", thumbnail="https://mock/f7", tags=[], storage_key="videos/f7.mp4"),
            FileUsage(file_id="p7-f7", project_id="p7-project", chapter_id=chapter2.id, shot_id="p7-s7", usage_kind="generated_video", source_ref="test:s7"),
        ])
        await db.commit()

        by_chapter = await precheck_clips_export(
            db, project_id="p7-project", selection=ClipsExportSelection(chapter_ids=["p7-ch"])
        )
        assert by_chapter.selected_count == 6
        assert all(item.chapter_id == "p7-ch" for item in by_chapter.items)

        by_scene = await precheck_clips_export(
            db, project_id="p7-project", selection=ClipsExportSelection(scene_group_ids=["p7-g2"])
        )
        assert [item.shot_id for item in by_scene.items] == ["p7-s3", "p7-s5", "p7-s6"]

        cross = await precheck_clips_export(
            db, project_id="p7-project", selection=ClipsExportSelection(shot_ids=["p7-s7", "p7-s1"])
        )
        assert [item.file_name for item in cross.items] == [
            "E01_SC01_SH001.mp4",
            "E02_SC01_SH001.mp4",
        ]
        assert cross.can_download
    await engine.dispose()
