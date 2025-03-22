from contextlib import asynccontextmanager
from datetime import date
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from api.cache_utils import price_history_key_builder, DateJsonCoder
from cache import redis_client
from dal import DataAccessLayer
from fly_client.client import FlyoneClient
from logs import custom_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with redis_client() as redis_cache:
            FastAPICache.init(RedisBackend(redis_cache), prefix="api-cache")
            yield
    except Exception as e:
        custom_logger.error(f"Error during lifespan setup: {e}")
        raise


app = FastAPI(lifespan=lifespan)


@app.get('/ping')
async def ping():
    return {'ping': 'pong'}

@app.get('/price-history/{src}/{dst}')
@cache(
    expire=300,
    key_builder=price_history_key_builder,
    coder=DateJsonCoder,
)  # Cache for 5 minutes
async def price_history(src: str, dst: str, dt: date | None = None):
    return await DataAccessLayer.get_direction_price_history(src.upper(), dst.upper(), dt)

@app.get('/airports')
@cache(expire=3600)  # Cache for 1 hour
async def airports():
    """Proxy endpoint to fetch airports from Flyone API."""
    fc = FlyoneClient()
    custom_logger.info('Fetching airports')
    return await fc.airport_by_code
