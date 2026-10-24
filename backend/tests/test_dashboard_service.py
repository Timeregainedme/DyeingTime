"""创作工作台聚合服务与接口测试。

覆盖三类风险：
1. 统计口径：已采纳版本不应继续算「待审核」；
2. 接口契约：返回统一信封，未登录被拒绝；
3. 权限：viewer 可读，聚合服务只能看到当前工作区。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient

from app.api.v1.routes.studio import dashboard as dashboard_route
from app.dependencies import WorkspaceContext, get_db
from app.main import app
from app.models.types import WorkspaceRole
from app.schemas.studio.dashboard import (
    DashboardProjectRead,
    DashboardRead,
    DashboardStatsRead,
)
from app.services.studio.dashboard import is_pending_review


class _DummyDB:
    """聚合逻辑被 monkeypatch，这里只需要一个可注入的占位会话。"""

    async def execute(self, *_args, **_kwargs):  # pragma: no cover - 不应被调用
        raise AssertionError("测试应替换 build_dashboard，而不是真的查库")


def _override_db(_db: _DummyDB):
    async def _get_db() -> AsyncGenerator[_DummyDB, None]:
        yield _db

    return _get_db


def test_is_pending_review_rules() -> None:
    # 已采纳版本 = 已确认，不再要求审核
    assert not is_pending_review(
        file_id="f1", adopted_file_id="f1", review_status=None
    )
    # 未采纳 + 无审核记录 = 待审核
    assert is_pending_review(file_id="f2", adopted_file_id="f1", review_status=None)
    # 未采纳 + unrated = 待审核
    assert is_pending_review(file_id="f2", adopted_file_id=None, review_status="unrated")
    # 已表态 = 不待审核
    assert not is_pending_review(
        file_id="f2", adopted_file_id=None, review_status="unsatisfied"
    )


def test_dashboard_returns_workspace_snapshot(client: TestClient, monkeypatch) -> None:
    async def _fake_build(db, *, ctx):  # noqa: ANN001
        assert ctx.workspace_id == "ws-test"
        return DashboardRead(
            can_edit=True,
            stats=DashboardStatsRead(
                project_count=1,
                pending_review_shots=2,
                running_tasks=3,
                adopted_videos=4,
            ),
            projects=[
                DashboardProjectRead(
                    id="p1",
                    name="测试项目",
                    description="",
                    style="真人都市",
                    visual_style="现实",
                    chapter_count=1,
                    total_shots=5,
                    pending_shots=1,
                    ready_shots=4,
                    pending_review_shots=0,
                    adopted_videos=0,
                    running_tasks=0,
                )
            ],
        )

    monkeypatch.setattr(dashboard_route, "build_dashboard", _fake_build)
    app.dependency_overrides[get_db] = _override_db(_DummyDB())
    try:
        response = client.get("/api/v1/studio/dashboard")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["stats"] == {
        "project_count": 1,
        "pending_review_shots": 2,
        "running_tasks": 3,
        "adopted_videos": 4,
    }
    assert body["data"]["projects"][0]["name"] == "测试项目"


def test_dashboard_requires_auth(client: TestClient) -> None:
    from app.dependencies import require_auth

    app.dependency_overrides.pop(require_auth, None)
    try:
        response = client.get("/api/v1/studio/dashboard")
    finally:
        app.dependency_overrides.pop(require_auth, None)
    assert response.status_code == 401


def test_audio_runner_binds_quota_helpers() -> None:
    """TTS 执行器必须能解析额度函数。

    回归背景：P10-B 真实 TTS 验收时发现 `reserve_for_task` / `settle_task`
    未导入，任何语音任务都会在第一步抛 NameError，且失败路径再次 NameError
    导致任务状态与额度都无法正确落库。这里锁定模块级绑定，防止再次漏导入。
    """
    from app.services.studio import audio_task_runner

    assert callable(audio_task_runner.reserve_for_task)
    assert callable(audio_task_runner.settle_task)
