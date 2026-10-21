"""http_logging 辅助函数单测。"""

from __future__ import annotations

from app.core.integrations.http_logging import redact_headers, safe_body_for_log_openai


def test_redact_headers_masks_authorization() -> None:
    h = {"Authorization": "Bearer secret", "Content-Type": "application/json"}
    out = redact_headers(h)
    assert out["Authorization"] == "***redacted***"
    assert out["Content-Type"] == "application/json"


def test_safe_body_for_log_openai_truncates_prompt() -> None:
    long_prompt = "x" * 400
    body = {"prompt": long_prompt, "n": 1}
    safe = safe_body_for_log_openai(body)
    assert "truncated" in safe["prompt"]
    assert len(safe["prompt"]) < len(long_prompt)
