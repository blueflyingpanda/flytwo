import pytest
from fakeredis import FakeAsyncRedis

from db import ASession, Base, async_engine


@pytest.fixture(autouse=True)
async def setup_test_db():
    """
    Fixture to create database schema at the beginning of the test session.
    Ensures all tables are created before any tests run.
    """
    if not async_engine.url.get_backend_name() == 'sqlite':
        raise RuntimeError('Use SQLite backend to run tests')

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with async_engine.begin() as conn:
        # drop tables after tests are done
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session():
    async with ASession() as session:
        yield session


@pytest.fixture
def redis_fake():
    return FakeAsyncRedis()


@pytest.fixture
def redis_mock(monkeypatch, redis_fake):
    def mock_redis_factory(*args, **kwargs):
        return redis_fake

    # Patch the Redis constructor in redis.asyncio module
    monkeypatch.setattr('redis.asyncio.Redis', mock_redis_factory)

    yield
