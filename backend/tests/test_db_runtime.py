from app.core.db import async_session_maker, reset_db_runtime


def test_async_session_maker_proxy_survives_runtime_reset() -> None:
    before_proxy_id = id(async_session_maker)

    reset_db_runtime()

    after_proxy_id = id(async_session_maker)
    session = async_session_maker()
    try:
        assert before_proxy_id == after_proxy_id
        assert session.__class__.__name__ == "AsyncSession"
    finally:
        # 这里只验证代理和重绑定行为，不实际打开连接。
        session.sync_session.close()
