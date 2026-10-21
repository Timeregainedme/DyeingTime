"""演员图片（ActorImage）schemas。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.studio import AssetQualityLevel, AssetViewAngle


class ActorImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: str
    quality_level: AssetQualityLevel = AssetQualityLevel.low
    view_angle: AssetViewAngle = AssetViewAngle.front
    file_id: str | None = None
    width: int | None = None
    height: int | None = None
    format: str = "png"

