"""P3 / C6：长剧本分块。

按行顺序切块，保留上下文重叠，不截断正文；
每块的 ``start_char`` / ``end_char`` 对应完整原文，供证据定位。
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MAX_CHARS = 6000
DEFAULT_OVERLAP_LINES = 4


@dataclass(frozen=True, slots=True)
class ScriptChunk:
    id: str
    index: int
    text: str
    start_char: int
    end_char: int


def split_script_for_parse(
    text: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_lines: int = DEFAULT_OVERLAP_LINES,
) -> list[ScriptChunk]:
    """按行切块；单行超长时按字符窗口继续切分。"""
    if not text.strip():
        return []

    lines = text.splitlines(keepends=True)
    if not lines:
        return []

    # 预计算每行起始偏移，便于把块边界映射回完整原文。
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)
    offsets.append(cursor)

    chunks: list[ScriptChunk] = []
    line_index = 0
    total_lines = len(lines)
    while line_index < total_lines:
        start_line = line_index
        end_line = start_line
        current_chars = 0
        while end_line < total_lines:
            line_len = len(lines[end_line])
            if current_chars + line_len > max_chars and end_line > start_line:
                break
            current_chars += line_len
            end_line += 1
        # 单行本身超过 max_chars：按字符窗口切，避免整块超限。
        if end_line == start_line + 1 and len(lines[start_line]) > max_chars:
            line = lines[start_line]
            for window_start in range(0, len(line), max_chars):
                window = line[window_start : window_start + max_chars]
                chunk_start = offsets[start_line] + window_start
                chunks.append(
                    ScriptChunk(
                        id=f"chunk-{len(chunks) + 1}",
                        index=len(chunks) + 1,
                        text=window,
                        start_char=chunk_start,
                        end_char=chunk_start + len(window),
                    )
                )
            line_index = end_line
            continue

        chunk_start = offsets[start_line]
        chunk_end = offsets[end_line]
        chunks.append(
            ScriptChunk(
                id=f"chunk-{len(chunks) + 1}",
                index=len(chunks) + 1,
                text=text[chunk_start:chunk_end],
                start_char=chunk_start,
                end_char=chunk_end,
            )
        )
        if end_line >= total_lines:
            break
        # 下一块从当前块尾部回退若干行，保留上下文；至少前进一行，避免死循环。
        overlap_start = max(start_line + 1, end_line - overlap_lines)
        line_index = overlap_start

    return chunks


__all__ = ["ScriptChunk", "DEFAULT_MAX_CHARS", "DEFAULT_OVERLAP_LINES", "split_script_for_parse"]
