"""P6：角色固定音色样本与 H3 参考音频编排。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.models.studio import (
    Chapter,
    Character,
    CharacterVoiceSample,
    FileItem,
    FileType,
    FileUsageKind,
    Project,
    Shot,
    ShotDialogLine,
)
from app.services.studio.file_usages import upsert_file_usage

MAX_AUDIO_BYTES = 30 * 1024 * 1024
_AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
_AUDIO_CT = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}


def _validate_audio(filename: str, content: bytes) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in _AUDIO_EXT:
        raise ValueError("音色样本只支持 mp3/wav/m4a/aac/ogg/flac")
    if not content or len(content) > MAX_AUDIO_BYTES:
        raise ValueError("音频为空或超过 30MB")
    head = content[:16]
    ok = (
        head.startswith(b"ID3")
        or head.startswith(b"RIFF")
        or head.startswith(b"fLaC")
        or head.startswith(b"OggS")
        or (head[4:8] == b"ftyp")
        or content[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}
    )
    if not ok:
        raise ValueError("音频内容与扩展名不匹配")
    return suffix


async def list_voice_samples(
    db: AsyncSession, *, character_id: str
) -> list[CharacterVoiceSample]:
    return list(
        (
            await db.execute(
                select(CharacterVoiceSample)
                .where(
                    CharacterVoiceSample.character_id == character_id,
                    CharacterVoiceSample.is_active.is_(True),
                )
                .order_by(CharacterVoiceSample.id.desc())
            )
        ).scalars().all()
    )


async def upload_voice_sample(
    db: AsyncSession,
    *,
    character: Character,
    file: UploadFile,
    label: str = "",
) -> CharacterVoiceSample:
    content = await file.read()
    suffix = _validate_audio(file.filename or "", content)
    key = f"voice-samples/{character.id}/{uuid.uuid4().hex}{suffix}"
    info = await storage.upload_file(
        key=key,
        data=content,
        content_type=_AUDIO_CT.get(suffix, "application/octet-stream"),
        extra_args={"ACL": "public-read"},
    )
    item = FileItem(
        id=str(uuid.uuid4()),
        type=FileType.audio,
        name=Path(file.filename or f"voice{suffix}").name,
        thumbnail=info.url,
        tags=[],
        storage_key=key,
    )
    db.add(item)
    await db.flush()
    await upsert_file_usage(
        db,
        file_id=item.id,
        project_id=character.project_id,
        chapter_id=None,
        shot_id=None,
        usage_kind=FileUsageKind.upload,
        source_ref=f"voice_sample:{character.id}:{item.id}",
    )
    sample = CharacterVoiceSample(
        character_id=character.id,
        file_id=item.id,
        label=label or item.name,
        is_active=True,
    )
    db.add(sample)
    await db.flush()
    return sample


async def deactivate_voice_sample(
    db: AsyncSession, *, character_id: str, sample_id: int
) -> None:
    sample = await db.get(CharacterVoiceSample, sample_id)
    if sample is None or sample.character_id != character_id:
        raise ValueError("音色样本不存在")
    sample.is_active = False
    await db.flush()


async def resolve_p6_audio_references(
    db: AsyncSession,
    *,
    shot_id: str,
    explicit_file_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """P6 路径解析 H3 音色参考。

    - 项目开关关闭：不添加任何音频；
    - 开启：按镜头对白说话人查找已启用固定样本；
    - 说话人不明确/缺少样本/超过 3 人：抛错，不回退到其他角色音频；
    - 不使用台词生成音频充当固定音色样本（旧视频入口保持原行为）。
    """
    shot = await db.get(Shot, shot_id)
    if shot is None:
        raise ValueError("镜头不存在")
    chapter = await db.get(Chapter, shot.chapter_id)
    project = await db.get(Project, chapter.project_id) if chapter else None
    if project is None or not bool(project.use_dialog_audio_as_reference):
        return []
    explicit = [str(item).strip() for item in (explicit_file_ids or []) if str(item).strip()]
    if explicit:
        if len(explicit) > 3:
            raise ValueError("参考音频最多 3 个")
        result = []
        for index, file_id in enumerate(explicit, start=1):
            file_item = await db.get(FileItem, file_id)
            if file_item is None or file_item.type != FileType.audio:
                raise ValueError(f"参考音频文件不存在或不是音频：{file_id}")
            result.append(
                {
                    "label": f"Audio {index}",
                    "file_id": file_id,
                    "speaker_name": "",
                    "speaker_id": "",
                    "line_index": None,
                }
            )
        return result

    lines = (
        await db.execute(
            select(ShotDialogLine)
            .where(ShotDialogLine.shot_detail_id == shot_id)
            .order_by(ShotDialogLine.index.asc(), ShotDialogLine.id.asc())
        )
    ).scalars().all()
    if not lines:
        return []
    characters = {
        item.id: item
        for item in (
            await db.execute(select(Character).where(Character.project_id == project.id))
        ).scalars().all()
    }
    speakers: list[tuple[Character, int]] = []
    seen: set[str] = set()
    for line in lines:
        character_id = str(line.speaker_character_id or "").strip()
        character = characters.get(character_id)
        if character is None:
            name = str(line.speaker_name or "").strip()
            matches = [item for item in characters.values() if item.name == name] if name else []
            if len(matches) != 1:
                raise ValueError(
                    f"台词行 {line.index} 的说话人无法唯一确定，请先在镜头编辑页关联说话角色"
                )
            character = matches[0]
        if character.id in seen:
            continue
        seen.add(character.id)
        speakers.append((character, int(line.index or 0)))
    if len(speakers) > 3:
        raise ValueError(f"参考音频说话人 {len(speakers)} 个，超过 H3 上限 3 个")
    result = []
    for index, (character, line_index) in enumerate(speakers, start=1):
        sample = (
            await db.execute(
                select(CharacterVoiceSample)
                .where(
                    CharacterVoiceSample.character_id == character.id,
                    CharacterVoiceSample.is_active.is_(True),
                    CharacterVoiceSample.file_id.is_not(None),
                )
                .order_by(CharacterVoiceSample.id.desc())
                .limit(1)
            )
        ).scalars().first()
        if sample is None or not sample.file_id:
            raise ValueError(
                f"角色「{character.name}」缺少固定音色样本；请在角色音色设置上传样本，"
                "或关闭项目“使用音色作为参考音频”"
            )
        file_item = await db.get(FileItem, sample.file_id)
        if file_item is None:
            raise ValueError(f"角色「{character.name}」的音色样本文件不存在")
        result.append(
            {
                "label": f"Audio {index}",
                "file_id": sample.file_id,
                "speaker_name": character.name,
                "speaker_id": "",
                "line_index": line_index,
            }
        )
    return result


__all__ = [
    "deactivate_voice_sample",
    "list_voice_samples",
    "resolve_p6_audio_references",
    "upload_voice_sample",
]
