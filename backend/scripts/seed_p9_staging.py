"""P9-A：为真实后端浏览器验收准备隔离测试数据（仅测试库/测试对象存储）。

不调用任何外部供应商。视频/图片使用本地 fixture；模型配置仅用于 UI 与 readiness。
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core import storage
from app.core.db import async_session_maker
from app.core.security import hash_password
from app.models.auth import User
from app.models.llm import Model, ModelSettings, Provider
from app.models.studio import (
    AssetImageCandidate,
    AssetVersion,
    Chapter,
    Character,
    FileItem,
    FileUsage,
    Project,
    ProjectPropLink,
    ProjectSceneLink,
    Prop,
    ProjectStyleOption,
    ProjectStyleSnapshot,
    Scene,
    SceneGroup,
    Shot,
    ShotAssetVersion,
    ShotDetail,
)
from app.models.studio_script_documents import ScriptDocument, ScriptDocumentVersion
from app.models.workspace import Workspace, WorkspaceMember

PNG = (Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "e2e-valid.png").read_bytes()


async def main() -> None:
    red = Path("tests/fixtures/p7_tiny_red.mp4").read_bytes()
    blue = Path("tests/fixtures/p7_tiny_blue.mp4").read_bytes()
    async with async_session_maker() as db:
        # 幂等清理测试对象（仅固定 E2E id）。
        from sqlalchemy import delete

        for model, ids in [
            (Project, ["p-e2e"]),
            (Workspace, ["ws-e2e"]),
            (User, [9001]),
            (Provider, ["prov-e2e"]),
            (ProjectStyleOption, ["style-e2e"]),
            (Model, ["model-text", "model-image", "model-video", "model-audio"]),
            (ModelSettings, [1]),
            (AssetVersion, ["av-scene", "av-char1", "av-char2", "av-prop"]),
            (Character, ["char-e2e-1", "char-e2e-2"]),
            (Scene, ["scene-e2e"]),
            (Prop, ["prop-e2e"]),
            (FileItem, ["f-char", "f-char2", "f-scene", "f-prop", "v-e2e-1", "v-e2e-2", "v-e2e-3", "v-e2e-4"]),
        ]:
            if model is User:
                await db.execute(delete(model).where(model.id.in_(ids)))
            else:
                await db.execute(delete(model).where(model.id.in_(ids)))
        await db.commit()

        user = User(id=9001, username="e2e", password_hash=hash_password("e2e-pass"), display_name="E2E 验收", is_active=True)
        ws = Workspace(id="ws-e2e", name="E2E 工作区", slug="e2e", description="", owner_id=user.id, is_active=True)
        db.add_all([user, ws, WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner", is_active=True)])
        db.add(ProjectStyleOption(
            id="style-e2e", visual_style="现实", name="真人都市",
            description="E2E 真人写实风格", prompt_pack="cinematic realistic urban drama",
            sort_order=1, is_builtin=True,
        ))
        provider = Provider(
            id="prov-e2e", name="compshare_model_api", base_url="http://127.0.0.1:9",
            image_base_url="http://127.0.0.1:9", video_base_url="http://127.0.0.1:9",
            audio_base_url="http://127.0.0.1:9", api_key="test-only", api_secret="",
            description="仅用于 UI/任务验收，不会调用", status="active", created_by="9001",
        )
        models = [
            Model(id="model-text", name="mock-text", category="text", provider_id=provider.id, params={}, description="", created_by="9001"),
            Model(id="model-image", name="mock-image", category="image", provider_id=provider.id, params={}, description="", created_by="9001"),
            Model(id="model-video", name="MiniMax-H3", category="video", provider_id=provider.id, params={"duration": 5}, description="", created_by="9001"),
            Model(id="model-audio", name="mock-audio", category="audio", provider_id=provider.id, params={}, description="", created_by="9001"),
        ]
        db.add_all([provider, *models])
        db.add(ModelSettings(id=1, default_text_model_id="model-text", fallback_text_model_id="model-text", default_image_model_id="model-image", default_video_model_id="model-video", default_audio_model_id="model-audio", api_timeout=30, log_level="info"))
        await db.flush()

        project = Project(
            id="p-e2e", workspace_id=ws.id, name="E2E 都市短剧", description="真实后端浏览器验收项目",
            style="真人都市", visual_style="现实", seed=1, unify_style=True, progress=40,
            default_video_ratio="9:16", use_dialog_audio_as_reference=False,
            default_image_model_id="model-image", default_video_model_id="model-video",
            default_audio_model_id="model-audio", default_reference_mode="reference",
            default_shot_duration=5, video_duration_min=4, video_duration_max=15,
            video_concurrency=4, created_by=9001,
        )
        chapter = Chapter(id="c-e2e", project_id=project.id, index=1, title="第1集：夜班", raw_text="林晚与周沉在医院值班室对话。")
        g1 = SceneGroup(id="g-e2e-1", project_id=project.id, chapter_id=chapter.id, index=1, title="值班室", description="", location="医院值班室", time_of_day="夜", story_event="发现钥匙")
        g2 = SceneGroup(id="g-e2e-2", project_id=project.id, chapter_id=chapter.id, index=2, title="走廊", description="", location="医院走廊", time_of_day="夜", story_event="追问")
        db.add_all([project, chapter])
        await db.flush()
        db.add_all([g1, g2])
        db.add(ProjectStyleSnapshot(
            project_id=project.id, source_style_id="style-e2e", style_name="真人都市",
            visual_style="现实", description="E2E", structured_profile={}, prompt_pack="cinematic realistic urban drama",
            reference_file_ids=[], sample_file_ids=[], snapshot_version=1, locked_at=datetime.now(UTC),
        ))
        await db.flush()

        scene = Scene(id="scene-e2e", name="医院值班室", description="", style=project.style, visual_style=project.visual_style)
        scene_version = AssetVersion(id="av-scene", project_id=project.id, asset_type="scene", asset_id=scene.id, version_no=1, version_kind="base", variant_type="base", name="医院值班室基础", status="active")
        scene.current_version_id = scene_version.id
        char1 = Character(id="char-e2e-1", project_id=project.id, name="林晚", description="护士", style=project.style, visual_style=project.visual_style, identity_locked_at=datetime.now(UTC), identity_lock_version=1)
        char2 = Character(id="char-e2e-2", project_id=project.id, name="周沉", description="医生", style=project.style, visual_style=project.visual_style, identity_locked_at=datetime.now(UTC), identity_lock_version=1)
        av1 = AssetVersion(id="av-char1", project_id=project.id, asset_type="character", asset_id=char1.id, version_no=1, version_kind="identity", variant_type="base", name="林晚身份", status="active")
        av2 = AssetVersion(id="av-char2", project_id=project.id, asset_type="character", asset_id=char2.id, version_no=1, version_kind="identity", variant_type="base", name="周沉身份", status="active")
        char1.identity_version_id = av1.id
        char2.identity_version_id = av2.id
        db.add_all([scene, scene_version, char1, char2, av1, av2, ProjectSceneLink(project_id=project.id, scene_id=scene.id)])
        await db.flush()

        async def put_file(file_id: str, name: str, key: str, data: bytes, content_type: str, ftype: str) -> FileItem:
            info = await storage.upload_file(key=key, data=data, content_type=content_type, extra_args={"ACL": "public-read"})
            item = FileItem(id=file_id, type=ftype, name=name, thumbnail=info.url, tags=[], storage_key=info.key)
            db.add(item)
            return item

        char_file = await put_file("f-char", "林晚.png", "e2e/images/char.png", PNG, "image/png", "image")
        char2_file = await put_file("f-char2", "周沉.png", "e2e/images/char2.png", PNG, "image/png", "image")
        scene_file = await put_file("f-scene", "值班室.png", "e2e/images/scene.png", PNG, "image/png", "image")
        prop_file = await put_file("f-prop", "钥匙.png", "e2e/images/prop.png", PNG, "image/png", "image")
        prop = Prop(id="prop-e2e", name="钥匙", description="", style=project.style, visual_style=project.visual_style)
        prop_version = AssetVersion(id="av-prop", project_id=project.id, asset_type="prop", asset_id=prop.id, version_no=1, version_kind="base", variant_type="base", name="钥匙基础", status="active")
        prop.current_version_id = prop_version.id
        db.add_all([prop, prop_version, ProjectPropLink(project_id=project.id, prop_id=prop.id)])
        await db.flush()
        db.add_all([
            AssetImageCandidate(project_id=project.id, asset_type="character", asset_id=char1.id, asset_version_id=av1.id, candidate_batch_id="e2e", view_angle="FRONT", source="uploaded", file_id=char_file.id, status="adopted", is_adopted=True, prompt="", generation_params={}, format="png"),
            AssetImageCandidate(project_id=project.id, asset_type="character", asset_id=char2.id, asset_version_id=av2.id, candidate_batch_id="e2e", view_angle="FRONT", source="uploaded", file_id=char2_file.id, status="adopted", is_adopted=True, prompt="", generation_params={}, format="png"),
            AssetImageCandidate(project_id=project.id, asset_type="prop", asset_id=prop.id, asset_version_id=prop_version.id, candidate_batch_id="e2e", view_angle="FRONT", source="uploaded", file_id=prop_file.id, status="adopted", is_adopted=True, prompt="", generation_params={}, format="png"),
            AssetImageCandidate(project_id=project.id, asset_type="scene", asset_id=scene.id, asset_version_id=scene_version.id, candidate_batch_id="e2e", view_angle="FRONT", source="uploaded", file_id=scene_file.id, status="adopted", is_adopted=True, prompt="", generation_params={}, format="png"),
            FileUsage(file_id=char_file.id, project_id=project.id, chapter_id=chapter.id, shot_id=None, usage_kind="asset_image", source_ref="e2e:char"),
            FileUsage(file_id=char2_file.id, project_id=project.id, chapter_id=chapter.id, shot_id=None, usage_kind="asset_image", source_ref="e2e:char2"),
            FileUsage(file_id=scene_file.id, project_id=project.id, chapter_id=chapter.id, shot_id=None, usage_kind="asset_image", source_ref="e2e:scene"),
            FileUsage(file_id=prop_file.id, project_id=project.id, chapter_id=chapter.id, shot_id=None, usage_kind="asset_image", source_ref="e2e:prop"),
        ])

        video_ids = ["v-e2e-1", "v-e2e-2", "v-e2e-3", "v-e2e-4"]
        for index, vid in enumerate(video_ids, start=1):
            data = red if index % 2 else blue
            item = await put_file(vid, f"shot-{index}.mp4", f"e2e/videos/{vid}.mp4", data, "video/mp4", "video")
            await db.flush()
            db.add(FileUsage(file_id=item.id, project_id=project.id, chapter_id=chapter.id, shot_id=None, usage_kind="generated_video", source_ref=f"e2e:{index}"))

        script_doc = ScriptDocument(id="sd-e2e", project_id=project.id, chapter_id=chapter.id, doc_type="episode", title="第1集：夜班")
        script_ver = ScriptDocumentVersion(id="sv-e2e", document_id=script_doc.id, version_no=1, file_id=None, file_name="第1集.md", file_type="md", content_hash="e2e", raw_text="夜班值班室，林晚与周沉发现一把钥匙。", text_length=20, status="active", parse_status="parsed")
        script_doc.current_version_id = script_ver.id
        script_doc.active_version_id = script_ver.id
        db.add_all([script_doc, script_ver])

        for index in range(1, 13):
            sid = f"s-e2e-{index}"
            adopted = video_ids[index - 1] if index <= 4 else None
            db.add(Shot(id=sid, chapter_id=chapter.id, scene_group_id=g1.id if index <= 6 else g2.id, index=index, title=f"镜头 {index}", status="ready", skip_extraction=True, generated_video_file_id=adopted))
            db.add(ShotDetail(id=sid, camera_shot="MS", angle="EYE_LEVEL", movement="STATIC", duration=5, video_prompt_draft="@林晚 与 @周沉 在值班室对视。"))
        await db.flush()
        for index in range(1, 13):
            sid = f"s-e2e-{index}"
            db.add(ShotAssetVersion(shot_id=sid, asset_type="character", asset_id=char1.id, asset_version_id=av1.id, role="character_identity", created_at=datetime.now(UTC)))
            if index in {2, 4}:
                db.add(ShotAssetVersion(shot_id=sid, asset_type="character", asset_id=char2.id, asset_version_id=av2.id, role="character_identity", created_at=datetime.now(UTC)))
            if index == 3:
                db.add(ShotAssetVersion(shot_id=sid, asset_type="prop", asset_id=prop.id, asset_version_id=prop_version.id, role="prop", created_at=datetime.now(UTC)))
            db.add(ShotAssetVersion(shot_id=sid, asset_type="scene", asset_id=scene.id, asset_version_id=scene_version.id, role="scene", created_at=datetime.now(UTC)))
        await db.commit()
        print("seeded p-e2e, user e2e/e2e-pass, videos", video_ids)


if __name__ == "__main__":
    asyncio.run(main())
