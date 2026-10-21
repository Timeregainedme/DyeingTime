from __future__ import annotations

from app.services.studio.generation.shared.types import GenerationSubmissionPayload
from app.services.studio.generation.video.build_base import VideoBaseDraft
from app.services.studio.generation.video.build_context import VideoGenerationContext
from app.services.studio.generation.video.derive_preview import derive_video_preview


async def build_video_submission_payload(
    db,
    *,
    base: VideoBaseDraft,
    context: VideoGenerationContext,
) -> GenerationSubmissionPayload:
    derived = await derive_video_preview(db, base=base, context=context)
    return GenerationSubmissionPayload(
        kind="video",
        prompt=derived.rendered_prompt,
        images=derived.images,
        extra={
            "prompt_preview": {
                "shot_id": derived.shot_id,
                "template_id": derived.template_id,
                "template_name": derived.template_name,
                "rendered_prompt": derived.rendered_prompt,
                "pack": derived.pack.model_dump(),
                "warnings": derived.warnings,
            }
        },
    )
