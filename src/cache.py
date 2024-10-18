from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis

from conf import REDIS_HOST, REDIS_PORT, REDIS_PASS, YC_CERT

@asynccontextmanager
async def redis_client() -> Redis:
    cache = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASS,
        ssl=True,
        ssl_ca_certs=YC_CERT,
    )
    try:
        yield cache
    finally:
        await cache.close()
