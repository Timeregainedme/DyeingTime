"""应用级注册入口：统一初始化供应商能力与任务执行器（均幂等）。"""

from __future__ import annotations


def bootstrap_all_registries() -> None:
    """启动时或惰性路径中调用一次即可；顺序固定为 provider 先于 task adapter。"""
    from app.core.tasks.bootstrap import bootstrap_task_adapters
    from app.services.llm.provider_bootstrap import bootstrap_builtin_providers

    bootstrap_builtin_providers()
    bootstrap_task_adapters()
