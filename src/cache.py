from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import redis.asyncio as redis
from redis.asyncio import Redis

from conf import REDIS_HOST, REDIS_PASS, REDIS_PORT
from logs import custom_logger


@asynccontextmanager
async def redis_client() -> AsyncGenerator[Redis, Any]:
    cache = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASS,
    )
    try:
        await cache.ping()
        custom_logger.info('Redis connection successful')
        yield cache
    except Exception as e:
        custom_logger.error(e)
    finally:
        await cache.aclose()
