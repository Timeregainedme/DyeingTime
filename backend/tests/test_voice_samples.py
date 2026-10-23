"""P6：固定音色样本与 H3 音频参考编排测试。"""

from __future__ import annotations

import io

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.datastructures import UploadFile

from app.core.db import Base
from app.core.storage import StoredFileInfo
from app.models.studio import Chapter, Character, Project, ProjectStyle, ProjectVisualStyle, Shot, ShotDetail, ShotDialogLine
from app.services.studio import voice_samples


async def _build():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return maker, engine


async def _seed(db: AsyncSession, *, use_audio: bool) -> tuple[Character, Shot]:
    project = Project(id="voice-project", workspace_id="ws-voice", name="音色", description="", style=ProjectStyle.real_people_city, visual_style=ProjectVisualStyle.live_action, use_dialog_audio_as_reference=use_audio)
    chapter = Chapter(id="voice-chapter", project_id=project.id, index=1, title="第1集", raw_text="")
    character = Character(id="voice-char", project_id=project.id, name="沈知微", description="", style=project.style, visual_style=project.visual_style)
    shot = Shot(id="voice-shot", chapter_id=chapter.id, index=1, title="镜头")
    detail = ShotDetail(id=shot.id, camera_shot="MS", angle="EYE_LEVEL", movement="STATIC", duration=5)
    db.add_all([project, chapter, character, shot, detail])
    db.add(ShotDialogLine(shot_detail_id=shot.id, index=1, text="你好。", speaker_character_id=character.id, speaker_name=character.name))
    await db.commit()
    return character, shot


@pytest.fixture(autouse=True)
def _storage(monkeypatch):
    async def _fake(*, key, data, content_type=None, extra_args=None):
        return StoredFileInfo(key=key, url=f"https://mock/{key}", size=len(data))

    monkeypatch.setattr(voice_samples.storage, "upload_file", _fake)


@pytest.mark.asyncio
async def test_audio_on_requires_fixed_sample_and_maps_speaker() -> None:
    maker, engine = await _build()
    async with maker() as db:
        character, shot = await _seed(db, use_audio=True)
        with pytest.raises(ValueError, match="缺少固定音色样本"):
            await voice_samples.resolve_p6_audio_references(db, shot_id=shot.id)
        upload = UploadFile(file=io.BytesIO(b"RIFF" + b"0" * 32), filename="sample.wav")
        sample = await voice_samples.upload_voice_sample(
            db, character=character, file=upload, label="固定音色"
        )
        await db.commit()
        refs = await voice_samples.resolve_p6_audio_references(db, shot_id=shot.id)
        assert len(refs) == 1
        assert refs[0]["file_id"] == sample.file_id
        assert refs[0]["speaker_name"] == "沈知微"
        assert refs[0]["label"] == "Audio 1"
    await engine.dispose()


@pytest.mark.asyncio
async def test_audio_off_adds_no_reference() -> None:
    maker, engine = await _build()
    async with maker() as db:
        _character, shot = await _seed(db, use_audio=False)
        assert await voice_samples.resolve_p6_audio_references(db, shot_id=shot.id) == []
    await engine.dispose()
