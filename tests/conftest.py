import pytest
from pytest_mock_resources import create_redis_fixture

from db import Base, async_engine, ASession


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


class MockRedis:
    async def ping(self):
        return True

    async def getdel(self, key):
        return b'valid_otp'

    async def aclose(self):
        pass


@pytest.fixture
def redis_mock(monkeypatch):
    def mock_redis_factory(*args, **kwargs):
        return MockRedis()

    # Patch the Redis constructor in redis.asyncio module
    monkeypatch.setattr('redis.asyncio.Redis', mock_redis_factory)

    yield

@pytest.fixture
def redis_patch(monkeypatch, redis_test):
    # Create a factory function to return redis db for testing
    def mock_redis_factory(*args, **kwargs):
        return redis_test

    # Patch the Redis constructor in redis.asyncio module
    monkeypatch.setattr('redis.asyncio.Redis', mock_redis_factory)

    yield
