"""P9-B1：为 4 个真实 H3 候选镜头生成参考绑定与不可变输入快照（不提交、不计费）。

只读业务资产 + 写入测试库的 binding/snapshot；不调用任何供应商。
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.db import async_session_maker
from app.models.studio import FileItem, Shot, ShotReferenceBinding
from app.services.studio.shot_references import build_generation_preview, create_snapshot

SHOTS = {
    "s-e2e-1": {
        "name": "单人角色近景",
        "refs": [("f-char", "character", "char-e2e-1", "av-char1", "character_identity"), ("f-scene", "scene", "scene-e2e", "av-scene", "scene")],
        "prompt": "<Subject 1> is the locked female lead. [Shot 1] At 00:00.000, she stands in the hospital duty room and slowly turns her head toward the camera, expression shifting from calm to doubt. <Picture 1> preserves her identity; <Picture 2> preserves the duty room.",
    },
    "s-e2e-2": {
        "name": "双人互动",
        "refs": [("f-char", "character", "char-e2e-1", "av-char1", "character_identity"), ("f-char2", "character", "char-e2e-2", "av-char2", "character_identity"), ("f-scene", "scene", "scene-e2e", "av-scene", "scene")],
        "prompt": "<Subject 1> and <Subject 2> are the two locked leads. [Shot 1] At 00:00.000, they talk in the duty room; he explains, she looks suspicious. <Picture 1> and <Picture 2> keep the two identities separate; <Picture 3> preserves the room.",
    },
    "s-e2e-3": {
        "name": "场景与道具",
        "refs": [("f-scene", "scene", "scene-e2e", "av-scene", "scene"), ("f-prop", "prop", "prop-e2e", "av-prop", "prop")],
        "prompt": "[Shot 1] At 00:00.000, the camera slowly pushes toward a key on the duty-room desk; cold light, no dialogue. <Picture 1> preserves the room; <Picture 2> preserves the key.",
    },
    "s-e2e-4": {
        "name": "Prompt 修改重抽",
        "refs": [("f-char", "character", "char-e2e-1", "av-char1", "character_identity"), ("f-char2", "character", "char-e2e-2", "av-char2", "character_identity"), ("f-scene", "scene", "scene-e2e", "av-scene", "scene")],
        "prompt": "<Subject 1> and <Subject 2> remain in the duty room. [Shot 1] At 00:00.000, she steps closer and studies his expression; camera slowly moves in. <Picture 1> and <Picture 2> keep identities; <Picture 3> preserves the room.",
    },
}


async def main() -> None:
    result = []
    async with async_session_maker() as db:
        for shot_id, spec in SHOTS.items():
            shot = await db.get(Shot, shot_id)
            if shot is None:
                raise SystemExit(f"missing test shot {shot_id}")
            # 清理该镜头旧的准备绑定（只影响测试库固定镜头）。
            old = (await db.execute(select(ShotReferenceBinding).where(ShotReferenceBinding.shot_id == shot_id))).scalars().all()
            for row in old:
                await db.delete(row)
            await db.flush()
            for index, (file_id, asset_type, asset_id, version_id, role) in enumerate(spec["refs"], start=1):
                if await db.get(FileItem, file_id) is None:
                    raise SystemExit(f"missing file {file_id}")
                db.add(ShotReferenceBinding(
                    shot_id=shot_id, file_id=file_id, asset_type=asset_type,
                    asset_id=asset_id, asset_version_id=version_id,
                    reference_role=role, source="manual", sort_order=index - 1,
                    is_pinned=True, is_active=True, created_by=9001,
                ))
            await db.flush()
            preview = await build_generation_preview(
                db, shot_id=shot_id, advanced_prompt=spec["prompt"], ratio="9:16",
                resolution="768p",
            )
            if preview.blocking_errors:
                raise SystemExit(f"{shot_id} preview blocked: {preview.blocking_errors}")
            snapshot = await create_snapshot(
                db, shot_id=shot_id, preview=preview, task_id=None, created_by=9001,
                request_key=f"p9-prep-{shot_id}",
            )
            result.append({
                "shot_id": shot_id, "name": spec["name"],
                "images": preview.images, "prompt": preview.prompt,
                "input_hash": preview.input_hash, "snapshot_id": snapshot.id,
                "duration": preview.duration, "ratio": preview.ratio,
                "resolution": preview.resolution,
            })
        await db.commit()
    print(json.dumps({"shots": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
