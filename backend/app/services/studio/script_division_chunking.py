"""分镜切分的分块与合并工具。

为什么要分块：整章一次 LLM 调用在长文本/慢模型上可能几分钟没有响应，
失败后整单重来。分块后可以并行、可以只重试失败块，并且每块输出更小、
校验失败面更窄。

这里只放纯函数，方便单测；真正的 LLM 调用仍在 worker 层。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.skills.script_processing import ScriptDivisionResult, ShotDivision

# 单块建议上限：约 1800 字或 120 行，二者先到为准。
DEFAULT_MAX_CHARS = 1800
DEFAULT_MAX_LINES = 120
MIN_CHUNK_CHARS = 200

# 常见时间轴标记：[00:00–00:04]、**[00:00-00:04]**、0:00-0:04 等。
_TIMESTAMP_LINE_RE = re.compile(
    r"^\s*\**\s*\[?\s*\d{1,2}:\d{2}\s*[–\-—~至]\s*\d{1,2}:\d{2}\s*\]?\s*\**",
)
_PUNCT_RE = re.compile(r"[\s，。！？；：、,.!?;:\-—–~（）()\[\]【】\"'“”‘’*#]+")


@dataclass(frozen=True)
class ScriptChunk:
    """一个待切分的文本块。行号是块内相对行号（1-based）。"""

    index: int
    text: str
    start_line: int
    end_line: int


class DivideChunkError(Exception):
    """单个分块切分失败。"""

    def __init__(self, chunk_index: int, message: str) -> None:
        super().__init__(f"第 {chunk_index + 1} 块切分失败：{message}")
        self.chunk_index = chunk_index
        self.message = message


class DivideChunksFailed(Exception):
    """多个分块失败；`errors` 供任务错误信息与前端重试使用。"""

    def __init__(self, errors: list[DivideChunkError]) -> None:
        super().__init__("；".join(str(item) for item in errors))
        self.errors = errors


def _line_groups_by_timestamp(lines: list[str]) -> list[tuple[int, int]] | None:
    """按时间轴标记行切组；没有标记时返回 None。"""
    starts = [index for index, line in enumerate(lines) if _TIMESTAMP_LINE_RE.match(line)]
    if len(starts) < 2:
        return None
    groups: list[tuple[int, int]] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        if end > start:
            groups.append((start, end))
    return groups or None


def _group_lines(
    lines: list[str],
    *,
    max_chars: int,
    max_lines: int,
) -> list[tuple[int, int]]:
    """无时间轴时按行数/字符数分组。"""
    groups: list[tuple[int, int]] = []
    start = 0
    chars = 0
    for index, line in enumerate(lines):
        line_len = len(line)
        would_exceed = index > start and (
            index - start >= max_lines or chars + line_len > max_chars
        )
        if would_exceed:
            groups.append((start, index))
            start = index
            chars = 0
        chars += line_len
    if start < len(lines):
        groups.append((start, len(lines)))
    return groups


def _merge_small_groups(
    lines: list[str],
    groups: list[tuple[int, int]],
    *,
    min_chars: int,
) -> list[tuple[int, int]]:
    """把过小的块并入下一块，避免模型只拿到一两行上下文。"""
    if len(groups) <= 1:
        return groups
    merged: list[tuple[int, int]] = []
    pending: tuple[int, int] | None = None
    for start, end in groups:
        if pending is not None:
            start = pending[0]
            pending = None
        text_len = sum(len(line) for line in lines[start:end])
        if text_len < min_chars and end < len(lines):
            pending = (start, end)
            continue
        merged.append((start, end))
    if pending is not None:
        if merged:
            merged[-1] = (merged[-1][0], pending[1])
        else:
            merged.append(pending)
    return merged


def split_script_for_division(
    script_text: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    max_lines: int = DEFAULT_MAX_LINES,
    min_chars: int = MIN_CHUNK_CHARS,
) -> list[ScriptChunk]:
    """把整章文本切成若干块。

    优先按显式时间轴标记切（短剧分镜稿常见）；否则按行数/字符数切。
    返回空列表表示没有可切分文本。
    """
    text = str(script_text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return []
    lines = text.split("\n")
    groups = _line_groups_by_timestamp(lines)
    if groups is None:
        groups = _group_lines(lines, max_chars=max_chars, max_lines=max_lines)
    groups = _merge_small_groups(lines, groups, min_chars=min_chars)

    chunks: list[ScriptChunk] = []
    for index, (start, end) in enumerate(groups):
        chunk_text = "\n".join(lines[start:end]).strip()
        if not chunk_text:
            continue
        chunks.append(
            ScriptChunk(
                index=len(chunks),
                text=chunk_text,
                start_line=start + 1,
                end_line=end,
            )
        )
    return chunks


def _normalize_excerpt(text: str) -> str:
    return _PUNCT_RE.sub("", str(text or ""))


def _is_boundary_duplicate(previous: ShotDivision, current: ShotDivision) -> bool:
    """判断相邻块边界是否重复同一镜头。"""
    prev = _normalize_excerpt(previous.script_excerpt)
    cur = _normalize_excerpt(current.script_excerpt)
    if not prev or not cur:
        return False
    if prev == cur:
        return True
    shorter, longer = (prev, cur) if len(prev) <= len(cur) else (cur, prev)
    return len(shorter) >= 12 and shorter in longer


def merge_chunk_shots(
    chunk_results: list[tuple[ScriptChunk, ScriptDivisionResult]],
) -> ScriptDivisionResult:
    """按块顺序合并镜头，去掉边界重复并重排 index。"""
    shots: list[ShotDivision] = []
    for _chunk, result in chunk_results:
        for shot in result.shots:
            excerpt = str(shot.script_excerpt or "").strip()
            if not excerpt:
                continue
            candidate = shot.model_copy(update={"script_excerpt": excerpt})
            if shots and _is_boundary_duplicate(shots[-1], candidate):
                # 保留前一块的版本；它通常包含更完整的开场上下文。
                continue
            shots.append(candidate)

    reindexed = [
        shot.model_copy(update={"index": index})
        for index, shot in enumerate(shots, start=1)
    ]
    return ScriptDivisionResult(
        shots=reindexed,
        total_shots=len(reindexed),
        notes=None,
    )
