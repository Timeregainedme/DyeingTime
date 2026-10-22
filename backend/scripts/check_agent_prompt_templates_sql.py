"""校验 Agent 提示词 SQL 与代码默认提示词逐字一致。

为什么需要它：
- 015 是已应用的全量种子，029 是后续 H3 Agent 更新迁移；权威文本是
  `app/chains/agents/*.py` 里的 `_*_SYSTEM_PROMPT` 常量。一旦有人只改代码不改 SQL，
  用户打开模板页不改内容直接点「发布生效」就会把**旧提示词**写进运行时（评审 B-5）。
- 本脚本不写文件，只做比对：解析 015 中的 UPDATE 语句，再用 029 的 H3 内容覆盖，
  还原被转义的内容后与生成器内存中的 `AGENT_TEMPLATES` 逐字比对。

用法：cd backend && uv run python scripts/check_agent_prompt_templates_sql.py
退出码：0 = 完全一致；1 = 存在差异或解析失败（可直接挂进 CI）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from scripts.gen_agent_prompt_templates_sql import AGENT_TEMPLATES  # noqa: E402

# 015 是已应用的全量种子，保持不变；029 是后续 H3 Agent 提示词更新迁移。
# 校验时把 029 的 H3 内容覆盖到 015 的解析结果上，再与代码默认逐字比对。
SQL_PATH = BACKEND_DIR / "sql" / "015-add-agent-prompt-templates.sql"
H3_UPDATE_PATH = BACKEND_DIR / "sql" / "029-update-h3-agent-prompt.sql"
DIVISION_UPDATE_PATH = BACKEND_DIR / "sql" / "032-update-script-division-agent-prompt.sql"
SCRIPT_AGENTS_UPDATE_PATH = BACKEND_DIR / "sql" / "033-update-script-agents-prompts.sql"
AGENT_UPDATE_PATHS: tuple[Path, ...] = (
    H3_UPDATE_PATH,
    DIVISION_UPDATE_PATH,
    SCRIPT_AGENTS_UPDATE_PATH,
)

# 生成器写出的 UPDATE 形态固定，这里按同一形态解析：
# UPDATE `prompt_templates` SET `name` = '<n>', `preview` = '<p>', `content` = '<c>', ...
_UPDATE_RE = re.compile(
    r"UPDATE `prompt_templates` SET `name` = '(?P<name>(?:[^']|'')*)', "
    r"`preview` = '(?P<preview>(?:[^']|'')*)', "
    r"`content` = '(?P<content>(?:[^']|'')*)', "
    r"`is_default` = 0, `is_system` = 0, `updated_at` = NOW\(\) "
    r"WHERE `category` = '(?P<category>[^']+)';",
    re.DOTALL,
)


def _unescape(value: str) -> str:
    """还原 `_sql_escape`：'' -> '、\\\\ -> \\。"""
    return value.replace("\\\\", "\\").replace("''", "'")


def _parse_sql_updates(text: str) -> dict[str, tuple[str, str, str]]:
    """解析 SQL 中每个 category 的 (name, preview, content)。"""
    parsed: dict[str, tuple[str, str, str]] = {}
    for match in _UPDATE_RE.finditer(text):
        category = match.group("category")
        parsed[category] = (
            _unescape(match.group("name")),
            _unescape(match.group("preview")),
            _unescape(match.group("content")),
        )
    return parsed


_AGENT_UPDATE_RE = re.compile(
    r"UPDATE `prompt_templates`\s+SET `content` = '(?P<content>(?:[^']|'')*)'.*?"
    r"WHERE `category` = '(?P<category>agent_[^']+)' AND `published_at` IS NULL;",
    re.DOTALL,
)


def _apply_agent_updates(parsed: dict[str, tuple[str, str, str]]) -> None:
    """把后续迁移（029/032...）的 Agent 提示词覆盖到 015 解析结果上。"""
    for path in AGENT_UPDATE_PATHS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for match in _AGENT_UPDATE_RE.finditer(text):
            category = match.group("category")
            if category not in parsed:
                continue
            name, preview, _old_content = parsed[category]
            parsed[category] = (name, preview, _unescape(match.group("content")))


def main() -> int:
    sql_text = SQL_PATH.read_text(encoding="utf-8")
    parsed = _parse_sql_updates(sql_text)
    _apply_agent_updates(parsed)

    problems: list[str] = []

    missing = sorted(set(AGENT_TEMPLATES) - set(parsed))
    extra = sorted(set(parsed) - set(AGENT_TEMPLATES))
    if missing:
        problems.append(f"SQL 缺失分类: {missing}")
    if extra:
        problems.append(f"SQL 多出分类: {extra}")

    for category, (name, preview, content) in AGENT_TEMPLATES.items():
        if category not in parsed:
            continue
        sql_name, sql_preview, sql_content = parsed[category]
        if (sql_name, sql_preview) != (name, preview):
            problems.append(f"{category}: name/preview 不一致")
        if sql_content != content:
            problems.append(f"{category}: content 与代码默认不一致")

    print(f"sql file        : {SQL_PATH}")
    print("agent updates   : " + ", ".join(path.name for path in AGENT_UPDATE_PATHS))
    print(f"templates(code) : {len(AGENT_TEMPLATES)}")
    print(f"templates(sql)  : {len(parsed)}")
    print(f"EXACT_MATCH: {not problems}")
    for item in problems:
        print(f"  - {item}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
