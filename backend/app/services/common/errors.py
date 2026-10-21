"""通用错误文案模板：统一 not found / already exists / required 等消息。"""

from __future__ import annotations

from collections.abc import Sequence


def entity_not_found(name: str) -> str:
    """实体不存在错误。"""
    return f"{name} not found"


def entity_already_exists(name: str) -> str:
    """实体已存在错误。"""
    return f"{name} already exists"


def required_field(field: str, *, when: str | None = None) -> str:
    """必填字段错误。"""
    if when:
        return f"{field} is required for {when}"
    return f"{field} is required"


def invalid_choice(field: str, choices: Sequence[str]) -> str:
    """字段取值非法错误。"""
    return f"{field} must be one of: {'/'.join(choices)}"


def not_belong_to(child_field: str, parent_field: str) -> str:
    """归属关系校验错误。"""
    return f"{child_field} does not belong to given {parent_field}"


def relation_mismatch(child_field: str, parent_field: str) -> str:
    """通用归属关系不匹配错误。"""
    return f"{child_field} does not belong to {parent_field}"
