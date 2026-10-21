"""仓库根级 pytest 入口适配。

作用：
- 从仓库根目录运行 pytest 时，自动将 backend/ 加入 sys.path
- 避免只能在 backend/ 目录内执行测试配置才生效
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parent / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def pytest_configure(config: pytest.Config) -> None:
    """根目录 pytest 运行时补齐 asyncio marker。"""
    config.addinivalue_line("markers", "asyncio: mark test as asyncio coroutine")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """在仓库根目录运行时，为 async 测试提供轻量执行器。

    说明：
    - backend/ 目录下通常会使用更完整的测试环境；
    - 根目录 `uv run pytest backend/tests ...` 时，可能没有安装 pytest-asyncio；
    - 这里用 asyncio.run 兜底执行 coroutine test，避免 async 用例被跳过。
    """

    if not inspect.iscoroutinefunction(pyfuncitem.obj):
        return None

    funcargs = {
        arg: pyfuncitem.funcargs[arg]
        for arg in pyfuncitem._fixtureinfo.argnames
        if arg in pyfuncitem.funcargs
    }
    asyncio.run(pyfuncitem.obj(**funcargs))
    return True
