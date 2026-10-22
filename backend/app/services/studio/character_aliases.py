"""P4：角色别名持久化与冲突检测。

别名是「同一个 Character 的可匹配称谓」，不是新的角色。这里只做增删改查与
冲突提示，绝不因为别名相同自动合并两个角色。
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import Character, CharacterAlias

_WHITESPACE = re.compile(r"\s+")


def normalize_alias(value: str) -> str:
    """统一别名：去首尾空白、压缩内部空白、转小写。"""
    return _WHITESPACE.sub(" ", (value or "").strip()).lower()


async def list_aliases(db: AsyncSession, *, character_id: str) -> list[CharacterAlias]:
    return list(
        (
            await db.execute(
                select(CharacterAlias)
                .where(CharacterAlias.character_id == character_id)
                .order_by(CharacterAlias.id.asc())
            )
        ).scalars().all()
    )


async def alias_character_map(
    db: AsyncSession, *, project_id: str
) -> dict[str, str]:
    """项目内 normalized_alias → character_id，供 P3 解析预匹配。"""
    rows = (
        await db.execute(
            select(CharacterAlias.normalized_alias, CharacterAlias.character_id)
            .join(Character, Character.id == CharacterAlias.character_id)
            .where(Character.project_id == project_id)
        )
    ).all()
    return {str(alias): str(character_id) for alias, character_id in rows}


async def _find_conflict(
    db: AsyncSession,
    *,
    project_id: str,
    normalized_alias: str,
    exclude_character_id: str | None = None,
) -> CharacterAlias | None:
    """查找同项目下其它角色是否已占用该别名。"""
    stmt = (
        select(CharacterAlias)
        .join(Character, Character.id == CharacterAlias.character_id)
        .where(
            Character.project_id == project_id,
            CharacterAlias.normalized_alias == normalized_alias,
        )
        .limit(1)
    )
    if exclude_character_id:
        stmt = stmt.where(CharacterAlias.character_id != exclude_character_id)
    return (await db.execute(stmt)).scalars().first()


async def add_alias(
    db: AsyncSession,
    *,
    character: Character,
    alias: str,
    source: str = "manual",
    created_by: int | None = None,
    reject_conflict: bool = True,
) -> CharacterAlias | None:
    """新增别名；冲突时默认抛错，P3 自动导入可静默跳过。

    返回 None 表示 P3 导入时因冲突跳过，不代表已存在同名角色。
    """
    raw = (alias or "").strip()
    normalized = normalize_alias(raw)
    if not normalized:
        raise ValueError("别名不能为空")
    if normalized == normalize_alias(character.name):
        return None

    existing = (
        await db.execute(
            select(CharacterAlias).where(
                CharacterAlias.character_id == character.id,
                CharacterAlias.normalized_alias == normalized,
            )
        )
    ).scalars().first()
    if existing is not None:
        return existing

    conflict = await _find_conflict(
        db,
        project_id=character.project_id,
        normalized_alias=normalized,
        exclude_character_id=character.id,
    )
    if conflict is not None:
        if not reject_conflict:
            return None
        conflict_character = await db.get(Character, conflict.character_id)
        raise ValueError(
            f"别名「{raw}」已被角色「{conflict_character.name if conflict_character else conflict.character_id}」占用，"
            "请人工确认是否合并角色"
        )

    row = CharacterAlias(
        character_id=character.id,
        alias=raw,
        normalized_alias=normalized,
        source=source,
        created_by=created_by,
    )
    db.add(row)
    await db.flush()
    return row


async def update_alias(
    db: AsyncSession,
    *,
    character: Character,
    alias_id: int,
    alias: str,
) -> CharacterAlias:
    row = await db.get(CharacterAlias, alias_id)
    if row is None or row.character_id != character.id:
        raise ValueError("别名不存在")
    raw = (alias or "").strip()
    normalized = normalize_alias(raw)
    if not normalized:
        raise ValueError("别名不能为空")
    conflict = await _find_conflict(
        db,
        project_id=character.project_id,
        normalized_alias=normalized,
        exclude_character_id=character.id,
    )
    if conflict is not None:
        raise ValueError("别名已被同项目其它角色占用，请人工确认是否合并角色")
    row.alias = raw
    row.normalized_alias = normalized
    await db.flush()
    return row


async def delete_alias(db: AsyncSession, *, character: Character, alias_id: int) -> None:
    row = await db.get(CharacterAlias, alias_id)
    if row is None or row.character_id != character.id:
        raise ValueError("别名不存在")
    await db.delete(row)
    await db.flush()


async def import_aliases(
    db: AsyncSession,
    *,
    character: Character,
    aliases: list[str],
    source: str = "p3_parse",
    created_by: int | None = None,
) -> list[str]:
    """批量导入别名，跳过冲突项并返回被跳过值，供 P3 记录提示。"""
    skipped: list[str] = []
    for alias in aliases:
        raw = (alias or "").strip()
        if not raw:
            continue
        try:
            result = await add_alias(
                db,
                character=character,
                alias=raw,
                source=source,
                created_by=created_by,
                reject_conflict=False,
            )
            if result is None and normalize_alias(raw) not in {
                normalize_alias(item.alias) for item in await list_aliases(db, character_id=character.id)
            }:
                skipped.append(raw)
        except ValueError:
            skipped.append(raw)
    return skipped


__all__ = [
    "add_alias",
    "alias_character_map",
    "delete_alias",
    "import_aliases",
    "list_aliases",
    "normalize_alias",
    "update_alias",
]
