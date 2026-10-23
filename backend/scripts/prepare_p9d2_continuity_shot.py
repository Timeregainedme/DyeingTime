"""P9-D2：准备一个用于背景连续性与双人构图验证的隔离测试镜头。

只操作本地验收库中的固定测试 ID；不修改原 `s-e2e-2`、历史快照或生产数据。
该镜头使用三张真实参考图：

- 男性角色（原男性肖像）
- 女性角色（原女性肖像）
- 办公室场景（原办公室图）

并通过一条结构化男性台词验证：指定说话人发声、另一角色保持沉默、
整个 5 秒镜头保持同一办公室空间与连续运镜。
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete

from app.core.db import async_session_maker
from app.models.studio import (
    AssetImageCandidate,
    AssetVersion,
    Chapter,
    Character,
    FileItem,
    FileUsage,
    Project,
    ProjectSceneLink,
    Scene,
    Shot,
    ShotAssetVersion,
    ShotDetail,
    ShotDialogLine,
    ShotGenerationSnapshot,
    ShotReferenceBinding,
)
from app.models.studio_shots import ShotCharacterLink
from app.models.types import FileUsageKind, ShotStatus
from app.services.studio.shot_references import build_generation_preview

PROJECT_ID = "p-e2e"
CHAPTER_ID = "c-e2e"
SHOT_ID = "s-p9d2-continuity"
MALE_ID = "char-p9d2-male"
FEMALE_ID = "char-p9d2-female"
SCENE_ID = "scene-p9d2-office"
MALE_VERSION_ID = "av-p9d2-male"
FEMALE_VERSION_ID = "av-p9d2-female"
SCENE_VERSION_ID = "av-p9d2-office"
MALE_FILE_ID = "f-p9d2-male"
FEMALE_FILE_ID = "f-p9d2-female"
SCENE_FILE_ID = "f-p9d2-office"
DIALOGUE_TEXT = "你听我解释。"
MALE_VOICE = "Young adult male voice, clear timbre, moderate pace, restrained emotion."
FEMALE_VOICE = "Adult female voice, calm and controlled."
NATURAL_PROMPT = "@顾言 与 @沈知微 在办公室内相对而立，顾言开口解释，沈知微保持沉默。"


async def _reset(db) -> None:
    await db.execute(delete(ShotGenerationSnapshot).where(ShotGenerationSnapshot.shot_id == SHOT_ID))
    await db.execute(delete(ShotReferenceBinding).where(ShotReferenceBinding.shot_id == SHOT_ID))
    await db.execute(delete(ShotDialogLine).where(ShotDialogLine.shot_detail_id == SHOT_ID))
    await db.execute(delete(ShotCharacterLink).where(ShotCharacterLink.shot_id == SHOT_ID))
    await db.execute(delete(ShotAssetVersion).where(ShotAssetVersion.shot_id == SHOT_ID))
    await db.execute(delete(ProjectSceneLink).where(ProjectSceneLink.shot_id == SHOT_ID))
    await db.execute(delete(Shot).where(Shot.id == SHOT_ID))
    await db.execute(
        delete(AssetImageCandidate).where(
            AssetImageCandidate.project_id == PROJECT_ID,
            AssetImageCandidate.asset_id.in_([MALE_ID, FEMALE_ID, SCENE_ID]),
        )
    )
    await db.execute(delete(Character).where(Character.id.in_([MALE_ID, FEMALE_ID])))
    await db.execute(delete(Scene).where(Scene.id == SCENE_ID))
    await db.execute(
        delete(AssetVersion).where(
            AssetVersion.id.in_([MALE_VERSION_ID, FEMALE_VERSION_ID, SCENE_VERSION_ID])
        )
    )
    await db.execute(
        delete(FileUsage).where(
            FileUsage.file_id.in_([MALE_FILE_ID, FEMALE_FILE_ID, SCENE_FILE_ID])
        )
    )
    await db.execute(
        delete(FileItem).where(FileItem.id.in_([MALE_FILE_ID, FEMALE_FILE_ID, SCENE_FILE_ID]))
    )
    await db.commit()


async def main() -> None:
    async with async_session_maker() as db:
        project = await db.get(Project, PROJECT_ID)
        chapter = await db.get(Chapter, CHAPTER_ID)
        if project is None or chapter is None:
            raise SystemExit("请先运行 scripts/seed_p9_staging.py 准备 p-e2e / c-e2e")

        await _reset(db)
        now = datetime.now(UTC)
        male_version = AssetVersion(
            id=MALE_VERSION_ID,
            project_id=project.id,
            asset_type="character",
            asset_id=MALE_ID,
            version_no=1,
            version_kind="identity",
            variant_type="base",
            name="顾言身份",
            status="active",
        )
        female_version = AssetVersion(
            id=FEMALE_VERSION_ID,
            project_id=project.id,
            asset_type="character",
            asset_id=FEMALE_ID,
            version_no=1,
            version_kind="identity",
            variant_type="base",
            name="沈知微身份",
            status="active",
        )
        scene_version = AssetVersion(
            id=SCENE_VERSION_ID,
            project_id=project.id,
            asset_type="scene",
            asset_id=SCENE_ID,
            version_no=1,
            version_kind="base",
            variant_type="base",
            name="办公室基础",
            status="active",
        )
        male = Character(
            id=MALE_ID,
            project_id=project.id,
            name="顾言",
            description="成年男性，短剧背景连续性验证角色",
            style=project.style,
            visual_style=project.visual_style,
            identity_locked_at=now,
            identity_lock_version=1,
            identity_version_id=male_version.id,
            voice_description=MALE_VOICE,
        )
        female = Character(
            id=FEMALE_ID,
            project_id=project.id,
            name="沈知微",
            description="成年女性，短剧背景连续性验证角色",
            style=project.style,
            visual_style=project.visual_style,
            identity_locked_at=now,
            identity_lock_version=1,
            identity_version_id=female_version.id,
            voice_description=FEMALE_VOICE,
        )
        scene = Scene(
            id=SCENE_ID,
            name="办公室 D2",
            description="现代办公室，黑色玻璃隔断、长走廊、米色沙发和暖色台灯",
            style=project.style,
            visual_style=project.visual_style,
            current_version_id=scene_version.id,
        )
        db.add_all(
            [
                male_version,
                female_version,
                scene_version,
                male,
                female,
                scene,
            ]
        )
        await db.flush()

        male_file = FileItem(
            id=MALE_FILE_ID,
            type="image",
            name="顾言.jpg",
            thumbnail="http://127.0.0.1:5000/dyeingtime-e2e/e2e/images/char.jpg",
            tags=[],
            storage_key="e2e/images/char.jpg",
        )
        female_file = FileItem(
            id=FEMALE_FILE_ID,
            type="image",
            name="沈知微.jpg",
            thumbnail="http://127.0.0.1:5000/dyeingtime-e2e/e2e/images/char2.jpg",
            tags=[],
            storage_key="e2e/images/char2.jpg",
        )
        scene_file = FileItem(
            id=SCENE_FILE_ID,
            type="image",
            name="办公室.jpg",
            thumbnail="http://127.0.0.1:5000/dyeingtime-e2e/e2e/images/scene.jpg",
            tags=[],
            storage_key="e2e/images/scene.jpg",
        )
        db.add_all([male_file, female_file, scene_file])
        await db.flush()

        db.add_all(
            [
                AssetImageCandidate(
                    project_id=project.id,
                    asset_type="character",
                    asset_id=male.id,
                    asset_version_id=male_version.id,
                    candidate_batch_id="p9d2",
                    view_angle="FRONT",
                    source="uploaded",
                    file_id=male_file.id,
                    status="adopted",
                    is_adopted=True,
                    adopted_at=now,
                    adopted_by=9001,
                    prompt="",
                    generation_params={},
                    format="jpg",
                ),
                AssetImageCandidate(
                    project_id=project.id,
                    asset_type="character",
                    asset_id=female.id,
                    asset_version_id=female_version.id,
                    candidate_batch_id="p9d2",
                    view_angle="FRONT",
                    source="uploaded",
                    file_id=female_file.id,
                    status="adopted",
                    is_adopted=True,
                    adopted_at=now,
                    adopted_by=9001,
                    prompt="",
                    generation_params={},
                    format="jpg",
                ),
                AssetImageCandidate(
                    project_id=project.id,
                    asset_type="scene",
                    asset_id=scene.id,
                    asset_version_id=scene_version.id,
                    candidate_batch_id="p9d2",
                    view_angle="FRONT",
                    source="uploaded",
                    file_id=scene_file.id,
                    status="adopted",
                    is_adopted=True,
                    adopted_at=now,
                    adopted_by=9001,
                    prompt="",
                    generation_params={},
                    format="jpg",
                ),
                FileUsage(
                    file_id=male_file.id,
                    project_id=project.id,
                    chapter_id=chapter.id,
                    shot_id=None,
                    usage_kind=FileUsageKind.asset_image.value,
                    source_ref="p9d2:male",
                ),
                FileUsage(
                    file_id=female_file.id,
                    project_id=project.id,
                    chapter_id=chapter.id,
                    shot_id=None,
                    usage_kind=FileUsageKind.asset_image.value,
                    source_ref="p9d2:female",
                ),
                FileUsage(
                    file_id=scene_file.id,
                    project_id=project.id,
                    chapter_id=chapter.id,
                    shot_id=None,
                    usage_kind=FileUsageKind.asset_image.value,
                    source_ref="p9d2:scene",
                ),
            ]
        )

        shot = Shot(
            id=SHOT_ID,
            chapter_id=chapter.id,
            scene_group_id="g-e2e-1",
            index=100,
            title="P9-D2 背景连续性与双人构图验证",
            script_excerpt="顾言向沈知微解释，沈知微保持沉默。",
            status=ShotStatus.ready,
            skip_extraction=True,
        )
        detail = ShotDetail(
            id=SHOT_ID,
            camera_shot="MS",
            angle="EYE_LEVEL",
            movement="STATIC",
            scene_id=scene.id,
            duration=5,
            description="顾言与沈知微在办公室内相对而立，顾言开口解释，沈知微沉默注视。",
            action_beats=["顾言开口解释", "沈知微保持沉默"],
            video_prompt_draft=NATURAL_PROMPT,
            atmosphere="安静的办公室，低声对峙",
        )
        db.add_all([shot, detail])
        await db.flush()

        db.add_all(
            [
                ShotCharacterLink(shot_id=shot.id, character_id=male.id, index=0, note="P9-D2 speaker"),
                ShotCharacterLink(shot_id=shot.id, character_id=female.id, index=1, note="P9-D2 silent listener"),
                ShotAssetVersion(
                    shot_id=shot.id,
                    asset_type="character",
                    asset_id=male.id,
                    asset_version_id=male_version.id,
                    role="character_identity",
                    slot=0,
                    source="plan",
                    created_at=now,
                ),
                ShotAssetVersion(
                    shot_id=shot.id,
                    asset_type="character",
                    asset_id=female.id,
                    asset_version_id=female_version.id,
                    role="character_identity",
                    slot=1,
                    source="plan",
                    created_at=now,
                ),
                ShotAssetVersion(
                    shot_id=shot.id,
                    asset_type="scene",
                    asset_id=scene.id,
                    asset_version_id=scene_version.id,
                    role="scene",
                    slot=0,
                    source="plan",
                    created_at=now,
                ),
                ProjectSceneLink(
                    project_id=project.id,
                    chapter_id=chapter.id,
                    shot_id=shot.id,
                    scene_id=scene.id,
                ),
                ShotReferenceBinding(
                    shot_id=shot.id,
                    file_id=male_file.id,
                    asset_type="character",
                    asset_id=male.id,
                    asset_version_id=male_version.id,
                    reference_role="character_identity",
                    source="manual",
                    sort_order=0,
                    is_pinned=True,
                    is_active=True,
                    created_by=9001,
                ),
                ShotReferenceBinding(
                    shot_id=shot.id,
                    file_id=female_file.id,
                    asset_type="character",
                    asset_id=female.id,
                    asset_version_id=female_version.id,
                    reference_role="character_identity",
                    source="manual",
                    sort_order=1,
                    is_pinned=True,
                    is_active=True,
                    created_by=9001,
                ),
                ShotReferenceBinding(
                    shot_id=shot.id,
                    file_id=scene_file.id,
                    asset_type="scene",
                    asset_id=scene.id,
                    asset_version_id=scene_version.id,
                    reference_role="scene",
                    source="manual",
                    sort_order=2,
                    is_pinned=True,
                    is_active=True,
                    created_by=9001,
                ),
                ShotDialogLine(
                    shot_detail_id=shot.id,
                    index=1,
                    text=DIALOGUE_TEXT,
                    line_mode="DIALOGUE",
                    emotion="克制，压低声音",
                    speaker_character_id=male.id,
                    speaker_name=male.name,
                ),
            ]
        )
        await db.commit()

        preview = await build_generation_preview(
            db,
            shot_id=shot.id,
            natural_prompt=NATURAL_PROMPT,
            ratio="9:16",
            resolution="768p",
        )
        print("shot_id:", shot.id)
        print("character_ids:", male.id, female.id)
        print("scene_id:", scene.id)
        print("input_hash:", preview.input_hash)
        print("images:", preview.images)
        print("warnings:", preview.warnings)
        print("blocking_errors:", preview.blocking_errors)
        print("prompt:\n", preview.prompt)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
