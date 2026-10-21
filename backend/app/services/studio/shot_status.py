"""镜头流程状态计算服务。

当前 `shot.status` 只表达“信息提取确认”是否闭环：

- pending：资产/对白候选仍有未确认项
- ready：候选已确认完成，或明确跳过提取

运行中的生成任务不再写入 `shot.status`，而应由任务系统单独表达。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.studio import (
    Shot,
    ShotCandidateStatus,
    ShotDialogueCandidateStatus,
    ShotExtractedCandidate,
    ShotExtractedDialogueCandidate,
    ShotStatus,
)
from app.services.common import entity_not_found


async def _count_candidates(db: AsyncSession, *, shot_id: str) -> tuple[int, int]:
    """统计镜头候选项总数和未处理数量。

    这里显式走 SQL 计数，避免在异步场景下访问 relationship
    触发隐式懒加载。
    """
    total_stmt = select(func.count(ShotExtractedCandidate.id)).where(
        ShotExtractedCandidate.shot_id == shot_id
    )
    unresolved_stmt = (
        select(func.count(ShotExtractedCandidate.id))
        .where(ShotExtractedCandidate.shot_id == shot_id)
        .where(ShotExtractedCandidate.candidate_status == ShotCandidateStatus.pending)
    )
    total = int(await db.scalar(total_stmt) or 0)
    unresolved = int(await db.scalar(unresolved_stmt) or 0)
    return total, unresolved


async def _count_dialogue_candidates(db: AsyncSession, *, shot_id: str) -> tuple[int, int]:
    """统计镜头对白候选项总数和未处理数量。"""
    total_stmt = select(func.count(ShotExtractedDialogueCandidate.id)).where(
        ShotExtractedDialogueCandidate.shot_id == shot_id
    )
    unresolved_stmt = (
        select(func.count(ShotExtractedDialogueCandidate.id))
        .where(ShotExtractedDialogueCandidate.shot_id == shot_id)
        .where(ShotExtractedDialogueCandidate.candidate_status == ShotDialogueCandidateStatus.pending)
    )
    total = int(await db.scalar(total_stmt) or 0)
    unresolved = int(await db.scalar(unresolved_stmt) or 0)
    return total, unresolved


async def recompute_shot_status(db: AsyncSession, *, shot_id: str) -> ShotStatus:
    """按镜头候选确认状态重新计算流程状态。"""
    shot = await db.get(Shot, shot_id)
    if shot is None:
        raise ValueError(entity_not_found("Shot"))

    if shot.skip_extraction:
        shot.status = ShotStatus.ready
        await db.flush()
        return shot.status

    if shot.last_extracted_at is None:
        shot.status = ShotStatus.pending
        await db.flush()
        return shot.status

    total_candidates, unresolved = await _count_candidates(db, shot_id=shot_id)
    total_dialogue_candidates, unresolved_dialogue = await _count_dialogue_candidates(db, shot_id=shot_id)
    if total_candidates == 0 and total_dialogue_candidates == 0:
        shot.status = ShotStatus.ready
        await db.flush()
        return shot.status

    shot.status = ShotStatus.ready if unresolved == 0 and unresolved_dialogue == 0 else ShotStatus.pending
    await db.flush()
    return shot.status


async def mark_shot_generating(db: AsyncSession, *, shot_id: str) -> ShotStatus:
    """兼容旧调用点：生成任务启动后只重算静态状态，不再写入 generating。

    这里保留函数，是为了避免在任务创建链路上到处改接口。
    后续可在所有调用点迁移完成后再删除。
    """
    return await recompute_shot_status(db, shot_id=shot_id)


def _count_candidates_sync(db: Session, *, shot_id: str) -> tuple[int, int]:
    total_stmt = select(func.count(ShotExtractedCandidate.id)).where(
        ShotExtractedCandidate.shot_id == shot_id
    )
    unresolved_stmt = (
        select(func.count(ShotExtractedCandidate.id))
        .where(ShotExtractedCandidate.shot_id == shot_id)
        .where(ShotExtractedCandidate.candidate_status == ShotCandidateStatus.pending)
    )
    total = int(db.scalar(total_stmt) or 0)
    unresolved = int(db.scalar(unresolved_stmt) or 0)
    return total, unresolved


def _count_dialogue_candidates_sync(db: Session, *, shot_id: str) -> tuple[int, int]:
    total_stmt = select(func.count(ShotExtractedDialogueCandidate.id)).where(
        ShotExtractedDialogueCandidate.shot_id == shot_id
    )
    unresolved_stmt = (
        select(func.count(ShotExtractedDialogueCandidate.id))
        .where(ShotExtractedDialogueCandidate.shot_id == shot_id)
        .where(ShotExtractedDialogueCandidate.candidate_status == ShotDialogueCandidateStatus.pending)
    )
    total = int(db.scalar(total_stmt) or 0)
    unresolved = int(db.scalar(unresolved_stmt) or 0)
    return total, unresolved


def recompute_shot_status_sync(db: Session, *, shot_id: str) -> ShotStatus:
    shot = db.get(Shot, shot_id)
    if shot is None:
        raise ValueError(entity_not_found("Shot"))

    if shot.skip_extraction:
        shot.status = ShotStatus.ready
        db.flush()
        return shot.status

    if shot.last_extracted_at is None:
        shot.status = ShotStatus.pending
        db.flush()
        return shot.status

    total_candidates, unresolved = _count_candidates_sync(db, shot_id=shot_id)
    total_dialogue_candidates, unresolved_dialogue = _count_dialogue_candidates_sync(db, shot_id=shot_id)
    if total_candidates == 0 and total_dialogue_candidates == 0:
        shot.status = ShotStatus.ready
        db.flush()
        return shot.status

    shot.status = ShotStatus.ready if unresolved == 0 and unresolved_dialogue == 0 else ShotStatus.pending
    db.flush()
    return shot.status
