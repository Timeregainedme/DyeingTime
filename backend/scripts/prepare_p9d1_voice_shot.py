"""P9-D1：准备一个只用于男性对白声音验证的隔离测试镜头。

该脚本只操作本地验收库中的固定测试 ID，不修改生产数据，也不修改历史
`s-e2e-1` 快照。它解决的原始矛盾是：

- 旧资产名为“林晚”，但采纳参考图实际是男性肖像；
- Prompt 同时出现 `female lead / she`；
- 原镜头没有 ShotDialogLine，也没有 voice_description。

这里不复用旧角色名/旧 Prompt，而是创建：

- 男性角色「江屿」，参考图仍是原男性肖像；
- 场景「办公室」，参考图仍是原办公室场景图；
- 一条结构化台词“你先听我解释。”；
- 用户明确填写的男性 voice_description；
- 正确的 ShotCharacterLink / ShotAssetVersion / Manifest 绑定。

运行方式（仅本地验收库）：

```bash
DATABASE_URL='mysql+aiomysql://root@localhost/p8_e2e?unix_socket=/tmp/opencode/mysql-p8.sock' \
JWT_SECRET='e2e-secret' \
.venv/bin/python scripts/prepare_p9d1_voice_shot.py
```
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select

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
    ShotReferenceBinding,
    ShotGenerationSnapshot,
)
from app.models.studio_shots import ShotCharacterLink
from app.models.types import FileUsageKind, ShotStatus
from app.services.studio.shot_references import build_generation_preview

PROJECT_ID = "p-e2e"
CHAPTER_ID = "c-e2e"
SCENE_GROUP_ID = "g-e2e-1"
SHOT_ID = "s-p9d1-voice"
CHARACTER_ID = "char-p9d1-male"
SCENE_ID = "scene-p9d1-office"
CHARACTER_VERSION_ID = "av-p9d1-male"
SCENE_VERSION_ID = "av-p9d1-office"
MALE_FILE_ID = "f-p9d1-male"
SCENE_FILE_ID = "f-p9d1-office"
DIALOGUE_TEXT = "你先听我解释。"
VOICE_DESCRIPTION = "年轻成年男性声音，音色清晰，语速适中，情绪克制。"
NATURAL_PROMPT = "@江屿 在办公室内站立，神情克制，缓慢抬眼看向镜头。"


async def _reset_fixed_rows(db) -> None:
    """清理上一次 P9-D1 固定测试数据，不触碰其他镜头/历史快照。"""
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
            AssetImageCandidate.asset_id.in_([CHARACTER_ID, SCENE_ID]),
        )
    )
    await db.execute(delete(Character).where(Character.id == CHARACTER_ID))
    await db.execute(delete(Scene).where(Scene.id == SCENE_ID))
    await db.execute(delete(AssetVersion).where(AssetVersion.id.in_([CHARACTER_VERSION_ID, SCENE_VERSION_ID])))
    await db.execute(delete(FileUsage).where(FileUsage.file_id.in_([MALE_FILE_ID, SCENE_FILE_ID])))
    await db.execute(delete(FileItem).where(FileItem.id.in_([MALE_FILE_ID, SCENE_FILE_ID])))
    await db.commit()


async def main() -> None:
    async with async_session_maker() as db:
        project = await db.get(Project, PROJECT_ID)
        chapter = await db.get(Chapter, CHAPTER_ID)
        if project is None or chapter is None:
            raise SystemExit("请先运行 scripts/seed_p9_staging.py 准备 p-e2e / c-e2e")

        await _reset_fixed_rows(db)
        now = datetime.now(UTC)

        character_version = AssetVersion(
            id=CHARACTER_VERSION_ID,
            project_id=project.id,
            asset_type="character",
            asset_id=CHARACTER_ID,
            version_no=1,
            version_kind="identity",
            variant_type="base",
            name="江屿身份",
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
        character = Character(
            id=CHARACTER_ID,
            project_id=project.id,
            name="江屿",
            description="成年男性，短剧专项声音验证角色",
            style=project.style,
            visual_style=project.visual_style,
            identity_locked_at=now,
            identity_lock_version=1,
            identity_version_id=character_version.id,
            voice_description=VOICE_DESCRIPTION,
        )
        scene = Scene(
            id=SCENE_ID,
            name="办公室",
            description="现代办公室，玻璃隔断与暖色台灯",
            style=project.style,
            visual_style=project.visual_style,
            current_version_id=scene_version.id,
        )
        db.add_all([character_version, scene_version, character, scene])
        await db.flush()

        male_file = FileItem(
            id=MALE_FILE_ID,
            type="image",
            name="江屿.jpg",
            thumbnail="http://127.0.0.1:5000/dyeingtime-e2e/e2e/images/char.jpg",
            tags=[],
            storage_key="e2e/images/char.jpg",
        )
        scene_file = FileItem(
            id=SCENE_FILE_ID,
            type="image",
            name="办公室.jpg",
            thumbnail="http://127.0.0.1:5000/dyeingtime-e2e/e2e/images/scene.jpg",
            tags=[],
            storage_key="e2e/images/scene.jpg",
        )
        db.add_all([male_file, scene_file])
        await db.flush()

        db.add_all(
            [
                AssetImageCandidate(
                    project_id=project.id,
                    asset_type="character",
                    asset_id=character.id,
                    asset_version_id=character_version.id,
                    candidate_batch_id="p9d1",
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
                    asset_type="scene",
                    asset_id=scene.id,
                    asset_version_id=scene_version.id,
                    candidate_batch_id="p9d1",
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
                    source_ref="p9d1:male",
                ),
                FileUsage(
                    file_id=scene_file.id,
                    project_id=project.id,
                    chapter_id=chapter.id,
                    shot_id=None,
                    usage_kind=FileUsageKind.asset_image.value,
                    source_ref="p9d1:scene",
                ),
            ]
        )

        shot = Shot(
            id=SHOT_ID,
            chapter_id=chapter.id,
            scene_group_id=SCENE_GROUP_ID,
            index=99,
            title="P9-D1 男性对白声音验证",
            script_excerpt="江屿：你先听我解释。",
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
            description="江屿站在办公室内，神情克制，缓慢抬眼看向镜头。",
            action_beats=["缓慢抬眼看向镜头", "开口说话"],
            video_prompt_draft=NATURAL_PROMPT,
            atmosphere="安静的室内，低声对峙",
        )
        db.add_all([shot, detail])
        await db.flush()
        db.add_all(
            [
                ShotCharacterLink(
                    shot_id=shot.id,
                    character_id=character.id,
                    index=0,
                    note="P9-D1 男性对白专项",
                ),
                ShotAssetVersion(
                    shot_id=shot.id,
                    asset_type="character",
                    asset_id=character.id,
                    asset_version_id=character_version.id,
                    role="character_identity",
                    slot=0,
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
                ShotReferenceBinding(
                    shot_id=shot.id,
                    file_id=male_file.id,
                    asset_type="character",
                    asset_id=character.id,
                    asset_version_id=character_version.id,
                    reference_role="character_identity",
                    source="manual",
                    sort_order=0,
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
                    sort_order=1,
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
                    speaker_character_id=character.id,
                    speaker_name=character.name,
                ),
            ]
        )
        await db.commit()

        # 只做不收费预览：确认最终 Prompt 不再有 female lead / she，且包含
        # 结构化台词、voice profile 与单一连续场景约束。
        preview = await build_generation_preview(
            db,
            shot_id=shot.id,
            natural_prompt=NATURAL_PROMPT,
            ratio="9:16",
            resolution="768p",
        )
        print("shot_id:", shot.id)
        print("character_id:", character.id)
        print("voice_description:", character.voice_description)
        print("input_hash:", preview.input_hash)
        print("warnings:", preview.warnings)
        print("blocking_errors:", preview.blocking_errors)
        print("images:", preview.images)
        print("prompt:\n", preview.prompt)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
