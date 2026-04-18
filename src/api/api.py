from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from aiogram import types
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from api import auth
from api.auth import User
from api.cache_utils import airports_key_builder, price_history_key_builder
from api.models import NotifyRequest, Ping, UserDirection
from bot.bot import bot, dp
from cache import redis_client
from client.client import Airport, FlyoneClient
from conf import BOT_SECRET, CORS_ORIGINS, DEBUG
from dal import DataAccessLayer
from logs import logger
from plotter import PriceHistory
from task_notify import main as notify_main


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with redis_client() as redis_cache:
            FastAPICache.init(RedisBackend(redis_cache), prefix='api-cache')
            yield
    except Exception as e:
        logger.error(f'Error during lifespan setup: {e}')
        raise


docs_url = '/docs' if DEBUG else None
redoc_url = '/redoc' if DEBUG else None

app = FastAPI(lifespan=lifespan, docs_url=docs_url, redoc_url=redoc_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth.router)


@app.get('/')
async def index(user: Annotated[User, Depends(auth.get_current_user)]) -> User:
    return user


@app.get('/ping')
async def ping() -> Ping:
    return Ping(ping='pong', pong='ping')


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
    logger.info('Fetching airports')
    airport_by_code = await fc.airport_by_code
    return list(airport_by_code.values())


@app.post('/webhook', include_in_schema=False)
async def webhook(request: Request) -> None:
    body = await request.json()
    update = types.Update(**body)
    await dp.feed_update(bot, update)


@app.post('/notify', status_code=status.HTTP_202_ACCEPTED, include_in_schema=False)
async def notify(
    request: NotifyRequest,
    background_tasks: BackgroundTasks,
    x_notify_secret: Annotated[str, Header()],
) -> None:
    if x_notify_secret != BOT_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid secret')
    background_tasks.add_task(notify_main, chat_id=request.chat_id, manual=request.manual)
