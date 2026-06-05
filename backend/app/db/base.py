"""SQLAlchemy declarative base and async session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# TODO(#42): NullPool 是 Phase 1 取舍 — 解决 Windows + pytest asyncpg 跨 event loop
# 复用 pooled connection 触发的稳定性 bug。生产环境每次 DB 请求新建 connection，
# 对 30 人 / 700 文档 MVP 影响有限。Phase 2 ACL 中间件落地前必须拆 dev/prod engine
# 配置（dev 保留 NullPool 测试隔离，prod 切 QueuePool）。详见 PR #14 review §3 Q2。
engine = create_async_engine(
    settings.postgres_url.get_secret_value(),
    echo=False,
    poolclass=NullPool,
)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
)
