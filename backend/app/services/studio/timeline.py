"""项目时间线聚合与成片导出。

设计要点：

- **聚合不落表**：镜头本身已经是「按章节顺序排列的片段」。时间线视图按
  `chapter.index` → `shot.index` 排序，用 `ShotDetail.duration` 累加出 `start`/`end`，
  不新建 `timeline_clips` 行，避免与镜头表产生第二份真相。
- **导出是显式动作**：只有全部片段都有已生成的视频时才允许导出；缺片段直接报
  可读的中文错误，而不是产出一个缺头少尾的残片。
- **归一化再拼接**：不同分镜的视频可能来自不同分辨率/是否带音轨的模型产出，
  直接 `-c copy` 拼接会在流结构不一致时失败。因此先逐段转成统一的
  「固定画幅 + 恒定帧率 + 必有音轨」的中间片，再用 concat 无重编码拼起来。
- ffmpeg 需要装在**后端容器**里（`deploy/docker/backend.Dockerfile` 的 apt 依赖）。
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import re
import shutil
import tempfile
import uuid
import zipfile
from collections.abc import Mapping
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.models.studio import (
    Chapter,
    FileItem,
    FileType,
    FileUsage,
    Project,
    SceneGroup,
    Shot,
    ShotDetail,
    ShotDialogLine,
    ShotFrameImage,
)
from app.schemas.studio.timeline import (
    ClipsExportItemRead,
    ClipsExportPrecheckRead,
    ClipsExportRequest,
    ClipsExportSelection,
    ProjectTimelineRead,
    TimelineClipRead,
    TimelineDialogRead,
    TimelineExportRead,
    TimelineFrameRead,
    TimelineStatsRead,
)
from app.services.common import create_and_refresh, entity_not_found
from app.services.studio.shot_dialogs import load_character_display_names, pick_display_name

# 成片目标画幅：按项目默认视频比例取接近的偶数尺寸，未知比例回落 16:9。
_EXPORT_TARGET_SIZE: dict[str, tuple[int, int]] = {
    "9:16": (720, 1280),
    "16:9": (1280, 720),
    "1:1": (1024, 1024),
    "4:3": (1024, 768),
    "3:4": (768, 1024),
    "21:9": (1680, 720),
    "3:2": (1152, 768),
    "2:3": (768, 1152),
}
_DEFAULT_EXPORT_SIZE = (1280, 720)
_ANULLSRC = "anullsrc=channel_layout=stereo:sample_rate=44100"


def _enum_text(value: object) -> str:
    """DB 里取出的枚举列是普通 str，也可能是 Enum，统一转成文本。"""
    return str(getattr(value, "value", value) or "")


def _export_size(ratio: str | None) -> tuple[int, int]:
    key = (ratio or "").strip()
    return _EXPORT_TARGET_SIZE.get(key, _DEFAULT_EXPORT_SIZE)


def _dialog_speaker_name(
    name_map: Mapping[str, str],
    line: ShotDialogLine,
) -> str | None:
    """时间轴字幕显示名：与对白列表/准备页走同一口径（角色真名优先，回落行内名字）。

    参数：
        name_map：角色 ID → 角色当前真名映射，由 :func:`load_character_display_names` 批量查询。
        line：台词行 ORM 对象。

    返回：
        显示名；沿用时间轴原有契约，空值统一归一为 ``None``（``TimelineDialogRead.speaker_name``
        是可空字段，字幕生成按「无说话人」处理）。
    """
    resolved = pick_display_name(
        name_map,
        character_id=line.speaker_character_id,
        fallback_name=line.speaker_name,
    )
    return (resolved or "").strip() or None


def _ffmpeg_binary(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise ValueError(
            f"服务器未安装 {name}，无法导出成片；请在后端镜像里安装 ffmpeg 后重试"
        )
    return found


async def _run_ffmpeg(args: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        _ffmpeg_binary("ffmpeg"),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        lines = stderr.decode("utf-8", "ignore").strip().splitlines()
        tail = " | ".join(line for line in lines[-8:] if line.strip())
        raise ValueError(f"ffmpeg 处理失败（exit={proc.returncode}）：{tail}")


async def _has_audio_stream(path: Path) -> bool:
    proc = await asyncio.create_subprocess_exec(
        _ffmpeg_binary("ffprobe"),
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return bool(stdout.strip())


async def _normalize_clip(src: Path, dst: Path, *, size: tuple[int, int]) -> None:
    """把一段分镜视频转成统一规格，保证可被 concat 无重编码拼接。"""
    width, height = size
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30"
    )
    codec_args = [
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        "-ac",
        "2",
    ]
    if await _has_audio_stream(src):
        mapping = ["-map", "0:v:0", "-map", "0:a:0"]
        inputs = ["-i", str(src)]
    else:
        # 没有音轨时补一条静音轨，否则拼接时各段流结构不一致会失败。
        inputs = ["-i", str(src), "-f", "lavfi", "-i", _ANULLSRC]
        mapping = ["-map", "0:v:0", "-map", "1:a:0", "-shortest"]
    await _run_ffmpeg(["-y", *inputs, *mapping, *codec_args, str(dst)])


async def get_project_timeline(db: AsyncSession, *, project_id: str) -> ProjectTimelineRead:
    """聚合出项目时间线视图（只读，不修改任何状态）。"""
    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(entity_not_found("Project"))

    chapters = (
        (
            await db.execute(
                select(Chapter)
                .where(Chapter.project_id == project_id)
                .order_by(Chapter.index.asc(), Chapter.id.asc())
            )
        )
        .scalars()
        .all()
    )

    chapter_meta: dict[str, tuple[int, str]] = {
        chapter.id: (int(chapter.index or 0), chapter.title or "") for chapter in chapters
    }

    shots: list[Shot] = []
    if chapter_meta:
        shots = list(
            (
                await db.execute(
                    select(Shot).where(Shot.chapter_id.in_(list(chapter_meta)))
                )
            )
            .scalars()
            .all()
        )
    shots.sort(key=lambda item: (chapter_meta.get(item.chapter_id, (0, ""))[0], item.index, item.id))

    scene_groups = (
        (
            await db.execute(
                select(SceneGroup)
                .where(SceneGroup.chapter_id.in_(list(chapter_meta)))
                .order_by(SceneGroup.index.asc(), SceneGroup.id.asc())
            )
        )
        .scalars()
        .all()
        if chapter_meta
        else []
    )
    scene_meta: dict[str, tuple[int, str]] = {
        group.id: (int(group.index or 0), group.title or "") for group in scene_groups
    }

    shot_ids = [shot.id for shot in shots]
    details: dict[str, ShotDetail] = {}
    frames: dict[str, list[ShotFrameImage]] = {}
    dialogs: dict[str, list[ShotDialogLine]] = {}
    if shot_ids:
        details = {
            detail.id: detail
            for detail in (
                await db.execute(select(ShotDetail).where(ShotDetail.id.in_(shot_ids)))
            )
            .scalars()
            .all()
        }
        for frame in (
            await db.execute(
                select(ShotFrameImage)
                .where(ShotFrameImage.shot_detail_id.in_(shot_ids))
                .order_by(ShotFrameImage.id.asc())
            )
        ).scalars().all():
            frames.setdefault(frame.shot_detail_id, []).append(frame)
        for line in (
            await db.execute(
                select(ShotDialogLine)
                .where(ShotDialogLine.shot_detail_id.in_(shot_ids))
                .order_by(
                    ShotDialogLine.shot_detail_id.asc(),
                    ShotDialogLine.index.asc(),
                    ShotDialogLine.id.asc(),
                )
            )
        ).scalars().all():
            dialogs.setdefault(line.shot_detail_id, []).append(line)

    # 字幕显示名统一口径：能解析到角色就显示角色真名，解析不到才回落行内名字（C-2）。
    dialog_name_map = await load_character_display_names(
        db,
        character_ids=[
            character_id
            for lines in dialogs.values()
            for line in lines
            for character_id in (line.speaker_character_id, line.target_character_id)
        ],
    )

    clips: list[TimelineClipRead] = []
    cursor = 0.0
    for shot in shots:
        detail = details.get(shot.id)
        duration = int(detail.duration or 0) if detail is not None else 0
        chapter_index, chapter_title = chapter_meta.get(shot.chapter_id, (0, ""))
        scene_index, scene_title = scene_meta.get(str(shot.scene_group_id or ""), (0, ""))
        start = cursor
        cursor += float(duration)
        video_file_id = str(shot.generated_video_file_id or "").strip() or None
        audio_file_id = str(shot.generated_audio_file_id or "").strip() or None
        clips.append(
            TimelineClipRead(
                shot_id=shot.id,
                chapter_id=shot.chapter_id,
                chapter_index=chapter_index,
                chapter_title=chapter_title,
                scene_group_id=str(shot.scene_group_id or "").strip() or None,
                scene_index=scene_index,
                scene_title=scene_title,
                index=int(shot.index or 0),
                title=shot.title or "",
                status=_enum_text(shot.status),
                duration=duration,
                start=start,
                end=cursor,
                video_file_id=video_file_id,
                audio_file_id=audio_file_id,
                thumbnail=shot.thumbnail or "",
                frames=[
                    TimelineFrameRead(
                        frame_type=_enum_text(frame.frame_type),
                        file_id=str(frame.file_id or "").strip() or None,
                        width=frame.width,
                        height=frame.height,
                        format=frame.format or "png",
                    )
                    for frame in frames.get(shot.id, [])
                ],
                dialogs=[
                    TimelineDialogRead(
                        line_id=line.id,
                        index=int(line.index or 0),
                        text=line.text or "",
                        emotion=(line.emotion or "").strip() or None,
                        speaker_name=_dialog_speaker_name(dialog_name_map, line),
                        audio_file_id=str(line.generated_audio_file_id or "").strip() or None,
                    )
                    for line in dialogs.get(shot.id, [])
                ],
            )
        )

    clips_with_video = sum(1 for clip in clips if clip.video_file_id)
    clips_with_audio = sum(
        1
        for clip in clips
        if clip.audio_file_id or any(dialog.audio_file_id for dialog in clip.dialogs)
    )
    stats = TimelineStatsRead(
        clip_count=len(clips),
        total_duration=cursor,
        clips_with_video=clips_with_video,
        clips_missing_video=len(clips) - clips_with_video,
        clips_with_audio=clips_with_audio,
        exportable=bool(clips) and clips_with_video == len(clips),
    )
    return ProjectTimelineRead(
        project_id=project.id,
        project_name=project.name or "",
        video_ratio=(project.default_video_ratio or "").strip() or None,
        clips=clips,
        stats=stats,
    )


async def export_project_timeline(db: AsyncSession, *, project_id: str) -> TimelineExportRead:
    """把项目下全部镜头按时间线顺序拼成一个成片文件。"""
    timeline = await get_project_timeline(db, project_id=project_id)
    if not timeline.clips:
        raise ValueError("该项目还没有分镜，无法导出成片")

    missing = [clip for clip in timeline.clips if not clip.video_file_id]
    if missing:
        titles = "、".join(f"第{clip.index}镜「{clip.title}」" for clip in missing[:5])
        suffix = "" if len(missing) <= 5 else f" 等 {len(missing)} 个"
        raise ValueError(f"还有 {len(missing)} 个分镜没有生成视频，无法导出成片：{titles}{suffix}")

    file_ids = [clip.video_file_id for clip in timeline.clips if clip.video_file_id]
    rows = (
        (await db.execute(select(FileItem).where(FileItem.id.in_(file_ids)))).scalars().all()
    )
    files_by_id = {item.id: item for item in rows}

    size = _export_size(timeline.video_ratio)
    workdir = Path(tempfile.mkdtemp(prefix="dyeingtime-export-"))
    try:
        normalized: list[Path] = []
        for position, clip in enumerate(timeline.clips, start=1):
            item = files_by_id.get(clip.video_file_id or "")
            if item is None:
                raise ValueError(f"分镜「{clip.title}」的视频文件记录已不存在，无法导出")
            payload = await storage.download_file(key=item.storage_key)
            source = workdir / f"src-{position:03d}.mp4"
            source.write_bytes(payload)
            target = workdir / f"norm-{position:03d}.mp4"
            await _normalize_clip(source, target, size=size)
            normalized.append(target)

        concat_list = workdir / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{path.name}'" for path in normalized) + "\n",
            encoding="utf-8",
        )
        output = workdir / "output.mp4"
        await _run_ffmpeg(
            [
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )
        result = output.read_bytes()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    key = f"exports/{project_id}/{uuid.uuid4()}.mp4"
    stored = await storage.upload_file(
        key=key,
        data=result,
        content_type="video/mp4",
        extra_args={"ACL": "public-read"},
    )
    name = f"{timeline.project_name or project_id}-成片.mp4"
    file_item = await create_and_refresh(
        db,
        FileItem(
            id=str(uuid.uuid4()),
            type=FileType.video,
            name=name,
            # 写入对象存储返回的公开 URL。
            # 之前这里硬编码空字符串，导致成片无法直接用 CDN 地址访问，
            # 只能回退到后端代理下载（占用 EC2 出网带宽，且 HEAD 请求会失败）。
            thumbnail=stored.url,
            tags=["export"],
            storage_key=key,
        ),
    )
    return TimelineExportRead(
        file_id=file_item.id,
        name=file_item.name,
        storage_key=file_item.storage_key,
        download_path=f"/api/v1/studio/files/{file_item.id}/download",
        clip_count=len(timeline.clips),
        duration=timeline.stats.total_duration,
    )


async def build_clips_archive(db: AsyncSession, *, project_id: str) -> tuple[bytes, str, int]:
    """把项目里所有已生成视频的片段打包成一个 zip。

    与「导出成片」的区别：
    - 导出成片是 ffmpeg 串成一个 mp4，需要全部片段都有视频；
    - 这里是把每个片段原样打包，允许部分片段缺失，缺失的会写进 MANIFEST 一并告知。

    返回值：(zip 字节, 下载文件名, 实际打包的片段数)。

    实现上先在内存里构建：zip 的中央目录在末尾，真流式需要先算偏移，
    对几十个片段的场景反而是过度设计；体积风险由调用方按片段数提示。
    """
    timeline = await get_project_timeline(db, project_id=project_id)
    clips = timeline.clips
    if not clips:
        raise ValueError("项目还没有任何片段")

    buffer = io.BytesIO()
    packed = 0
    missing: list[str] = []

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for clip in clips:
            label = f"{clip.chapter_index:02d}-{clip.index:02d}"
            safe_title = _sanitize_archive_name(clip.title or "clip")
            if not clip.video_file_id:
                missing.append(f"{label}-{safe_title}（未生成视频）")
                continue

            item = await db.get(FileItem, clip.video_file_id)
            if item is None:
                missing.append(f"{label}-{safe_title}（文件记录缺失）")
                continue

            try:
                content = await storage.download_file(key=item.storage_key)
            except Exception:  # noqa: BLE001 - 单个片段失败不阻断整包
                missing.append(f"{label}-{safe_title}（读取对象存储失败）")
                continue

            suffix = Path(item.storage_key).suffix or ".mp4"
            archive.writestr(f"{label}-{safe_title}{suffix}", content)
            packed += 1

        if missing:
            archive.writestr(
                "MANIFEST-未打包片段.txt",
                "以下片段没有被打包：\n\n" + "\n".join(missing) + "\n",
            )

    if packed == 0:
        raise ValueError("没有任何片段生成了视频，无法打包导出")

    filename = f"{_sanitize_archive_name(timeline.project_name or project_id)}-片段打包.zip"
    return buffer.getvalue(), filename, packed



# P7 导出资源保护：避免一次选择无限数量或超大素材拖垮进程。
MAX_EXPORT_CLIPS = 500
MAX_EXPORT_BYTES = 20 * 1024 * 1024 * 1024


class ClipsExportConflict(ValueError):
    """预检查后导出输入发生变化（采纳版本、文件等）。"""


def _clip_export_name(clip: TimelineClipRead) -> str:
    """导出命名：E01_SC02_SH003.mp4；未分配场次使用 SC00。"""
    scene_index = int(clip.scene_index or 0)
    return (
        f"E{int(clip.chapter_index or 0):02d}_SC{scene_index:02d}_"
        f"SH{int(clip.index or 0):03d}.mp4"
    )


def _plan_hash(project_id: str, items: list[ClipsExportItemRead]) -> str:
    """对选择集合、当前采纳文件和目标文件名做一次性快照 hash。"""
    payload = {
        "project_id": project_id,
        "items": [
            {
                "shot_id": item.shot_id,
                "file_id": item.file_id,
                "file_name": item.file_name,
                "status": item.status,
                "size_bytes": item.size_bytes,
            }
            for item in items
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


async def _selected_clips(
    db: AsyncSession,
    *,
    project_id: str,
    selection: ClipsExportSelection,
) -> tuple[Project, list[TimelineClipRead]]:
    """解析四种选择范围，并统一按剧集 → 场次 → 镜头业务顺序返回。"""
    timeline = await get_project_timeline(db, project_id=project_id)
    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(entity_not_found("Project"))
    scopes = [
        selection.shot_ids is not None,
        selection.scene_group_ids is not None,
        selection.chapter_ids is not None,
        bool(selection.include_all),
    ]
    if sum(1 for item in scopes if item) != 1:
        raise ValueError("请只指定一种导出范围：shot_ids / scene_group_ids / chapter_ids / include_all")

    selected: list[TimelineClipRead]
    if selection.shot_ids is not None:
        if not selection.shot_ids:
            raise ValueError("自定义镜头选择不能为空")
        if len(set(selection.shot_ids)) != len(selection.shot_ids):
            raise ValueError("自定义镜头选择包含重复 Shot ID")
        by_id = {clip.shot_id: clip for clip in timeline.clips}
        unknown = [shot_id for shot_id in selection.shot_ids if shot_id not in by_id]
        if unknown:
            raise ValueError("以下镜头不属于当前项目：" + "、".join(unknown[:10]))
        wanted = set(selection.shot_ids)
        selected = [clip for clip in timeline.clips if clip.shot_id in wanted]
    elif selection.scene_group_ids is not None:
        if not selection.scene_group_ids:
            raise ValueError("场次选择不能为空")
        rows = (
            await db.execute(
                select(SceneGroup.id).where(
                    SceneGroup.project_id == project_id,
                    SceneGroup.id.in_(selection.scene_group_ids),
                )
            )
        ).scalars().all()
        unknown = set(selection.scene_group_ids) - set(rows)
        if unknown:
            raise ValueError("以下场次不属于当前项目：" + "、".join(sorted(unknown)))
        wanted = set(selection.scene_group_ids)
        selected = [clip for clip in timeline.clips if clip.scene_group_id in wanted]
    elif selection.chapter_ids is not None:
        if not selection.chapter_ids:
            raise ValueError("剧集选择不能为空")
        rows = (
            await db.execute(
                select(Chapter.id).where(
                    Chapter.project_id == project_id,
                    Chapter.id.in_(selection.chapter_ids),
                )
            )
        ).scalars().all()
        unknown = set(selection.chapter_ids) - set(rows)
        if unknown:
            raise ValueError("以下剧集不属于当前项目：" + "、".join(sorted(unknown)))
        wanted = set(selection.chapter_ids)
        selected = [clip for clip in timeline.clips if clip.chapter_id in wanted]
    else:
        selected = list(timeline.clips)

    if not selected:
        raise ValueError("选择范围内没有镜头，无法导出")
    if len(selected) > MAX_EXPORT_CLIPS:
        raise ValueError(f"单次最多导出 {MAX_EXPORT_CLIPS} 个镜头")
    selected.sort(
        key=lambda item: (
            int(item.chapter_index or 0),
            # P5 的 shots.index 是剧集内全局故事顺序；场次只决定文件名 SCxx，
            # 未分配场次的 SC00 不能因此被排到所有正式场景之前。
            int(item.index or 0),
            int(item.scene_index or 0),
            item.shot_id,
        )
    )
    return project, selected


async def precheck_clips_export(
    db: AsyncSession,
    *,
    project_id: str,
    selection: ClipsExportSelection,
) -> ClipsExportPrecheckRead:
    """检查已采纳视频、文件记录、对象存储与 MP4 格式，返回计划快照。"""
    project, clips = await _selected_clips(db, project_id=project_id, selection=selection)
    file_ids = [str(clip.video_file_id) for clip in clips if clip.video_file_id]
    file_rows = (
        (await db.execute(select(FileItem).where(FileItem.id.in_(file_ids)))).scalars().all()
        if file_ids
        else []
    )
    files_by_id = {item.id: item for item in file_rows}
    usage_rows = (
        (
            await db.execute(
                select(FileUsage.file_id).where(
                    FileUsage.project_id == project_id,
                    FileUsage.file_id.in_(file_ids),
                )
            )
        ).scalars().all()
        if file_ids
        else []
    )
    allowed_file_ids = set(usage_rows)

    items: list[ClipsExportItemRead] = []
    semaphore = asyncio.Semaphore(6)

    async def _inspect(clip: TimelineClipRead) -> ClipsExportItemRead:
        file_name = _clip_export_name(clip)
        file_id = str(clip.video_file_id or "").strip() or None
        base = ClipsExportItemRead(
            shot_id=clip.shot_id,
            chapter_id=clip.chapter_id,
            chapter_index=int(clip.chapter_index or 0),
            chapter_title=clip.chapter_title,
            scene_group_id=clip.scene_group_id,
            scene_index=int(clip.scene_index or 0),
            scene_title=clip.scene_title,
            shot_index=int(clip.index or 0),
            title=clip.title,
            duration=int(clip.duration or 0),
            file_id=file_id,
            file_name=file_name,
        )
        if file_id is None:
            return base.model_copy(update={"status": "no_accepted", "error": "镜头尚未采纳视频"})
        item = files_by_id.get(file_id)
        if item is None:
            return base.model_copy(update={"status": "file_missing", "error": "视频文件记录不存在"})
        if file_id not in allowed_file_ids:
            return base.model_copy(update={"status": "file_missing", "error": "视频文件不属于当前项目"})
        if _enum_text(item.type) != "video":
            return base.model_copy(update={"status": "unsupported_format", "error": "文件类型不是视频"})
        suffix = Path(item.storage_key or "").suffix.lower()
        if suffix != ".mp4":
            return base.model_copy(
                update={
                    "status": "unsupported_format",
                    "error": f"实际文件不是 MP4（{suffix or '无扩展名'}），未做扩展名伪装",
                }
            )
        async with semaphore:
            try:
                info = await storage.get_file_info(key=item.storage_key)
            except Exception:  # noqa: BLE001 - 预检查要逐文件返回可操作错误
                return base.model_copy(
                    update={"status": "storage_unavailable", "error": "对象存储文件不可读取"}
                )
            content_type = (info.content_type or "").lower()
            if content_type and content_type not in {
                "video/mp4",
                "application/octet-stream",
                "binary/octet-stream",
            }:
                return base.model_copy(
                    update={
                        "status": "unsupported_format",
                        "error": f"对象存储 Content-Type 不是 MP4：{content_type}",
                    }
                )
            try:
                head = await storage.download_file(key=item.storage_key, byte_range=(0, 63))
            except Exception:  # noqa: BLE001
                return base.model_copy(
                    update={"status": "storage_unavailable", "error": "对象存储文件读取失败"}
                )
            if b"ftyp" not in head[:64]:
                return base.model_copy(
                    update={"status": "unsupported_format", "error": "文件头不是有效 MP4"}
                )
        return base.model_copy(
            update={"status": "ok", "size_bytes": int(info.size or 0)}
        )

    items = await asyncio.gather(*[_inspect(clip) for clip in clips])
    items = list(items)

    names = [item.file_name for item in items if item.status == "ok"]
    duplicate_names = {name for name in names if names.count(name) > 1}
    blockers: list[str] = []
    for index, item in enumerate(items):
        if item.file_name in duplicate_names:
            items[index] = item.model_copy(
                update={"status": "file_missing", "error": "ZIP 内文件名冲突"}
            )
    for item in items:
        if item.status != "ok":
            blockers.append(f"{item.file_name}：{item.error}")
    # 用稳定顺序重新计算（上一步可能已更新重复项）。
    plan_hash = _plan_hash(project_id, items)
    estimated_size = sum(item.size_bytes for item in items if item.status == "ok")
    if estimated_size > MAX_EXPORT_BYTES:
        blockers.append(
            f"预计导出大小 {estimated_size} 字节超过上限 {MAX_EXPORT_BYTES} 字节"
        )
    no_accepted = sum(1 for item in items if item.status == "no_accepted")
    file_missing = sum(1 for item in items if item.status == "file_missing")
    unsupported = sum(1 for item in items if item.status == "unsupported_format")
    exportable = sum(1 for item in items if item.status == "ok")
    return ClipsExportPrecheckRead(
        project_id=project.id,
        project_name=project.name or "",
        selected_count=len(items),
        exportable_count=exportable,
        no_accepted_count=no_accepted,
        file_missing_count=file_missing,
        unsupported_count=unsupported,
        total_duration=sum(float(item.duration) for item in items),
        estimated_size=estimated_size,
        plan_hash=plan_hash,
        can_download=not blockers and exportable == len(items) and bool(items),
        items=items,
        blockers=blockers,
    )


async def build_selected_clips_archive(
    db: AsyncSession,
    *,
    project_id: str,
    request: ClipsExportRequest,
) -> tuple[Path, str, int, str]:
    """严格按预检查结果构建 MP4-only ZIP；任何缺失都报错，不静默跳过。"""
    precheck = await precheck_clips_export(
        db, project_id=project_id, selection=request
    )
    if request.expected_plan_hash and request.expected_plan_hash != precheck.plan_hash:
        raise ClipsExportConflict("导出输入已变化（采纳版本或文件发生变化），请重新预检查")
    if not precheck.can_download:
        detail = "；".join(precheck.blockers[:8])
        if len(precheck.blockers) > 8:
            detail += f" 等 {len(precheck.blockers)} 项"
        raise ValueError("导出预检查未通过：" + detail)

    file_ids = [str(item.file_id) for item in precheck.items if item.file_id]
    rows = (
        (await db.execute(select(FileItem).where(FileItem.id.in_(file_ids)))).scalars().all()
    )
    files_by_id = {item.id: item for item in rows}
    workdir = Path(tempfile.mkdtemp(prefix="dyeingtime-clips-export-"))
    zip_path = workdir / "clips.zip"
    try:
        # ZIP_STORED：MP4 已压缩，避免重复 DEFLATE 的 CPU 放大；ZIP64 由 zipfile 自动处理。
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED, allowZip64=True) as archive:
            for index, item in enumerate(precheck.items, start=1):
                file_item = files_by_id.get(item.file_id or "")
                if file_item is None:
                    raise ValueError(f"{item.file_name}：视频文件记录在导出时消失")
                temp_path = workdir / f"src-{index:04d}.mp4"
                try:
                    await storage.download_file_to_path(
                        key=file_item.storage_key, path=temp_path
                    )
                    archive.write(
                        temp_path,
                        arcname=item.file_name,
                        compress_type=zipfile.ZIP_STORED,
                    )
                finally:
                    temp_path.unlink(missing_ok=True)
        filename = (
            f"DyeingTime_{_sanitize_archive_name(precheck.project_name or project_id)}_"
            f"{date.today():%Y%m%d}.zip"
        )
        return zip_path, filename, len(precheck.items), precheck.plan_hash
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise


def _sanitize_archive_name(value: str) -> str:
    """清掉文件名里的路径分隔符与非法字符，避免解压时出现目录穿越。"""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", value or "").strip(" ._")
    return cleaned[:80] or "clip"
