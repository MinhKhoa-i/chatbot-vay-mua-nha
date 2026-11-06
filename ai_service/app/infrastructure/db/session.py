from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.engine import make_url

from app.core.config import Settings


@lru_cache
def get_async_engine() -> AsyncEngine:
    settings = Settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    database_url = make_url(settings.database_url)
    if database_url.drivername == "postgresql":
        database_url = database_url.set(drivername="postgresql+asyncpg")
    return create_async_engine(database_url, pool_pre_ping=True)


@lru_cache
def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_async_engine(), expire_on_commit=False)


async def dispose_database() -> None:
    if get_async_engine.cache_info().currsize:
        await get_async_engine().dispose()
    get_async_session_factory.cache_clear()
    get_async_engine.cache_clear()
