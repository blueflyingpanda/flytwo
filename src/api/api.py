from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from api import auth
from api.auth import User
from api.cache_utils import price_history_key_builder, airports_key_builder
from api.models import UserDirection, Ping
from cache import redis_client
from client.client import FlyoneClient, Airport
from conf import CORS_ORIGINS
from dal import DataAccessLayer
from logs import custom_logger
from plotter import PriceHistory


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with redis_client() as redis_cache:
            FastAPICache.init(RedisBackend(redis_cache), prefix='api-cache')
            yield
    except Exception as e:
        custom_logger.error(f'Error during lifespan setup: {e}')
        raise


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get('/')
async def index(user: Annotated[User, Depends(auth.get_current_user)]) -> User:
    return user


@app.get('/ping')
async def ping() -> Ping:
    return Ping(ping='pong')


@app.get('/directions')
async def directions(user: Annotated[User, Depends(auth.get_current_user)]) -> list[UserDirection]:
    fetched = await DataAccessLayer.get_directions_by_chats([int(user.chat_id)])
    directions = list(fetched.values())

    if directions:
        directions = directions[0]

    return [UserDirection.model_validate(direction) for direction in directions]


@app.get('/price-history/{src}/{dst}', response_model=PriceHistory)
@cache(expire=300, key_builder=price_history_key_builder)  # Cache for 5 minutes
async def price_history(src: str, dst: str, dt: date | None = None) -> PriceHistory:
    direction_price_history = await DataAccessLayer.get_direction_price_history(src.upper(), dst.upper(), dt)
    return PriceHistory.model_validate(direction_price_history)


@app.get('/airports', response_model=list[Airport])
@cache(expire=3600, key_builder=airports_key_builder)  # Cache for 1 hour
async def airports() -> list[Airport]:
    """Proxy endpoint to fetch airports from Flyone API."""
    fc = FlyoneClient()
    custom_logger.info('Fetching airports')
    airport_by_code = await fc.airport_by_code
    return list(airport_by_code.values())
