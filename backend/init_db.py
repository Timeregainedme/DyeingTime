import asyncio

from app.core.db import init_db, close_db


async def _main() -> None:
    """初始化数据库，创建所有表。"""
    await init_db()
    await close_db()


if __name__ == "__main__":
    asyncio.run(_main())

