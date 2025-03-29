import pytest
from db import Base, async_engine, ASession


@pytest.fixture(scope='function', autouse=True)
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


@pytest.fixture(scope="function")
async def session():
        async with ASession() as session:
            yield session
