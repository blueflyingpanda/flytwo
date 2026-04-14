import asyncio
import json

from pydantic_core import to_jsonable_python
from redis.asyncio import Redis

import db
from bot.notifier import TgBotNotifier
from client.client import FLIGHTS_TYPE_ADAPTER, Flight, FlyoneClient, FlyoneError
from conf import REDIS_TTL
from dal import DataAccessLayer
from logs import logger


class FlightsFetcher:
    @staticmethod
    async def fetch_flights(
        direction: db.Direction, notifier: TgBotNotifier, cache: Redis, fc: FlyoneClient
    ) -> tuple[list[Flight], list[Flight], TgBotNotifier] | None:
        travel_date = direction.travel_date.isoformat()
        src = direction.src
        dst = direction.dst

        forward_key = backward_key = None
        forward_value = backward_value = None

        if REDIS_TTL is not None:
            forward_key = f'{src}{dst}{travel_date.replace("-", "")}'
            backward_key = f'{dst}{src}{travel_date.replace("-", "")}'

            forward_value, backward_value = await cache.mget(forward_key, backward_key)

        if forward_value is None or backward_value is None:
            try:
                logger.info('Fetching data from flyone: %s -> %s', src, dst)

                forward, backward = await fc.get_flights(
                    dep=src, arr=dst, dep_date=travel_date, arr_date=travel_date, currency='EUR'
                )
            except FlyoneError as e:
                err_msg = f'{e}'
                logger.error(err_msg)
                await notifier.send_err(err_msg)
                return None

            if REDIS_TTL is not None:
                await asyncio.gather(
                    cache.set(forward_key, json.dumps(forward, default=to_jsonable_python), ex=REDIS_TTL),
                    cache.set(backward_key, json.dumps(backward, default=to_jsonable_python), ex=REDIS_TTL),
                )

        else:
            logger.info('Cache found: %s -> %s', src, dst)

            forward: list[Flight] = FLIGHTS_TYPE_ADAPTER.validate_json(forward_value)
            backward: list[Flight] = FLIGHTS_TYPE_ADAPTER.validate_json(backward_value)

        await DataAccessLayer.add_flights(forward + backward)

        return forward, backward, notifier
