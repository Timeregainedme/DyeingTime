"""P6：角色固定音色样本 schemas。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VoiceSampleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: str
    file_id: str | None = None
    file_url: str = ""
    label: str = ""
    is_active: bool = True
