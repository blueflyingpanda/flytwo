from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

import redis.asyncio as redis
from redis.asyncio import Redis

from conf import REDIS_HOST, REDIS_PORT, REDIS_PASS, YC_CERT
from logs import custom_logger


@asynccontextmanager
async def redis_client() -> AsyncGenerator[Redis, Any]:
    cache = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASS,
        ssl=True,
        ssl_ca_certs=YC_CERT,
    )
    try:
        await cache.ping()
        custom_logger.info('Redis connection successful')
        yield cache
    except Exception as e:
        custom_logger.error(e)
    finally:
        await cache.aclose()
