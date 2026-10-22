"""P3 / C6：解析运行、候选审核与差异报告的请求响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScriptParseRequest(BaseModel):
    """开始解析本集。"""

    model_id: str | None = Field(None, description="可选文本模型 ID；默认全局文本模型")
    force: bool = Field(False, description="已有完成的同输入解析时是否强制重新解析")


class ScriptParseCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    candidate_type: str
    candidate_key: str
    order_index: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    review_status: str = "pending"
    matched_entity_id: str | None = None
    merged_into_id: str | None = None
    issue: str = ""
    created_at: datetime | None = None


class ScriptParseRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version_id: str
    worldbuilding_version_id: str | None = None
    task_id: str | None = None
    status: str
    progress: int = 0
    model_id: str | None = None
    model_name: str = ""
    provider_name: str = ""
    prompt_version: str = ""
    prompt_hash: str = ""
    chunk_count: int = 1
    failed_chunks: list[int] = Field(default_factory=list)
    error: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    confirmed_at: datetime | None = None
    confirmed_by: int | None = None
    applied_summary: dict[str, Any] | None = None
    confirmed_result: dict[str, Any] | None = None
    candidates: list[ScriptParseCandidateRead] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ScriptParseTaskRead(BaseModel):
    """开始解析的返回：run 状态 + 是否复用。"""

    run: ScriptParseRunRead
    reused: bool = False


class ScriptParseCandidateCreate(BaseModel):
    """人工新增一条候选。"""

    candidate_type: str = Field(..., description="character / scene / prop / costume_change / scene_beat / dialogue / episode / issue")
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class ScriptParseCandidateUpdate(BaseModel):
    """人工修改候选；只传需要改的字段。"""

    payload: dict[str, Any] | None = None
    review_status: str | None = Field(None, description="pending / edited / accepted / ignored")
    matched_entity_id: str | None = None
    issue: str | None = None


class ScriptParseMergeRequest(BaseModel):
    """把 source 候选合并到 target 候选。"""

    source_candidate_id: str
    target_candidate_id: str


class ScriptParseConfirmRead(BaseModel):
    run: ScriptParseRunRead
    applied_summary: dict[str, Any] = Field(default_factory=dict)
    reused: bool = False


class ScriptDiffRequest(BaseModel):
    """生成差异报告；old_version_id 为空时取当前生效版本。"""

    old_version_id: str | None = None


class ScriptDiffReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    old_version_id: str
    new_version_id: str
    status: str = "draft"
    text_diff: list[dict[str, Any]] = Field(default_factory=list)
    structured_diff: dict[str, Any] = Field(default_factory=dict)
    impact: dict[str, Any] = Field(default_factory=dict)
    decisions: dict[str, Any] = Field(default_factory=dict)
    decided_by: int | None = None
    decided_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ScriptDiffDecisionRequest(BaseModel):
    """接受/忽略差异报告；不会自动覆盖正式业务数据。"""

    status: str = Field(..., description="accepted / ignored")
    decisions: dict[str, Any] = Field(default_factory=dict)
