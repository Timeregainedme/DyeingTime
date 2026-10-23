"""P7 / C16：测试剧本模板、Fixtures 与真实 MP4 测试素材完整性。"""

from __future__ import annotations

from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "docs" / "test-scripts"
FIXTURES = TEMPLATES / "fixtures"


def test_three_markdown_and_docx_templates_exist_and_are_editable() -> None:
    stems = [
        "A-室内双人对话-template",
        "B-都市多场景-template",
        "C-单人悬疑-template",
    ]
    for stem in stems:
        md = TEMPLATES / f"{stem}.md"
        docx = TEMPLATES / f"{stem}.docx"
        assert md.is_file(), md
        assert docx.is_file(), docx
        assert md.stat().st_size > 500
        text = md.read_text(encoding="utf-8")
        assert "使用说明" in text
        assert "项目信息" in text
        # Word 模板必须能被 python-docx 打开且包含可见标题/占位说明。
        doc = Document(docx)
        paragraphs = "\n".join(item.text for item in doc.paragraphs)
        assert "剧本模板" in paragraphs
        assert "使用说明" in paragraphs


def test_non_empty_fixtures_exist() -> None:
    for name in ["A-室内双人对话.md", "B-都市多场景.md", "C-单人悬疑.md"]:
        path = FIXTURES / name
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        assert len(text) > 200
        assert "项目" in text
        assert "场景" in text or "场次" in text


def test_mock_mp4_fixtures_are_real_mp4_containers() -> None:
    for name in ["p7_tiny_red.mp4", "p7_tiny_blue.mp4"]:
        path = Path(__file__).parent / "fixtures" / name
        assert path.is_file()
        data = path.read_bytes()
        assert len(data) > 1000
        assert b"ftyp" in data[:64]
        assert data[4:8] == b"ftyp"
