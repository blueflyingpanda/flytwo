import asyncio
import json
import random
from collections import defaultdict
from decimal import Decimal

import aiohttp
from pydantic_core import to_jsonable_python
from redis.asyncio import Redis

from cache import redis_client
from conf import BOT_TOKEN, REDIS_TTL
from dal import DataAccessLayer
from fly_client.client import FlyoneClient, Flight, FlyoneException, FLIGHTS_TYPE_ADAPTER
from logs import custom_logger


class TgBotNotifier:

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    max_msg_len = 4096

    def __init__(self, chat_id: int, price_limit: Decimal | None, msg_header: str = ''):
        self.chat_id = chat_id
        self.price_limit = price_limit
        self.msg_header = msg_header

    def __hash__(self):
        return hash(self.chat_id)

    async def form_msg(self, flights: list[Flight]):

        msgs = []
        flights = [flight for flight in flights if self.price_limit is None or flight.price <= self.price_limit]

        for flight in flights:
            day, month, year = flight.travel_date.split('.')
            f_date = f'{day.zfill(2)}.{month.zfill(2)}.{year}'

            price = f'{flight.price}'

            msg = f'{f_date}: {flight.from_airport.code} -> {flight.to_airport.code} - {price.rjust(4)} {flight.currency}'

            msgs.append(msg)

        return '\n'.join(msgs) or 'not found 🥲'

    async def send_msgs(self, msgs: list[str]):

        async def slow_send():
            """fixes connection timeout to https://api.telegram.org"""
            await asyncio.sleep(random.uniform(0.1, 1.0))
            await session.post(self.url, json=payload, ssl=False)

        async with aiohttp.ClientSession() as session:
            to_send = []

            for msg in msgs:
                payload = {'text': f'{self.msg_header}\n\n{msg}', 'chat_id': self.chat_id}
                to_send.append(slow_send())

            await asyncio.gather(*to_send)

    async def send_err(self, msg: str):
        warn = '⚠️'
        err_msg = msg.partition(":")[2].strip()
        await self.send_msgs([f'{warn} {err_msg} {warn}'.strip()])


async def fetch_flights(
    src: str, dst: str, travel_date: str, msg_header: str, notifier: TgBotNotifier, cache: Redis, fc: FlyoneClient
) -> tuple[list[Flight], list[Flight], TgBotNotifier] | None:

    forward_key = backward_key = None
    forward_value = backward_value = None

    if REDIS_TTL is not None:
        forward_key = f'{src}{dst}{travel_date.replace("-", "")}'
        backward_key = f'{dst}{src}{travel_date.replace("-", "")}'

        forward_value, backward_value = await cache.mget(forward_key, backward_key)

    if forward_value is None or backward_value is None:
        try:
            custom_logger.info(f'Fetching data from flyone: {src} -> {dst}')

            forward, backward = await fc.get_flights(
                dep=src,
                arr=dst,
                dep_date=travel_date,
                arr_date=travel_date,
                currency='EUR'
            )
        except FlyoneException as e:
            err_msg = f'{e}'
            custom_logger.error(err_msg)
            await notifier.send_err(err_msg)
            return

        if REDIS_TTL is not None:
            await asyncio.gather(
                cache.set(forward_key, json.dumps(forward, default=to_jsonable_python), ex=REDIS_TTL),
                cache.set(backward_key, json.dumps(backward, default=to_jsonable_python), ex=REDIS_TTL)
            )
    else:
        custom_logger.info(f'Cache found: {src} -> {dst}')

        forward: list[Flight] = FLIGHTS_TYPE_ADAPTER.validate_json(forward_value)
        backward: list[Flight] = FLIGHTS_TYPE_ADAPTER.validate_json(backward_value)

    return forward, backward, notifier


async def main(event: dict | None = None, context=None):
    callee_chat_ids = None

    if event is not None and (body := event.get('body')):
        body = json.loads(body)
        chat_id = body.get('chat_id')
        if chat_id is not None:
            callee_chat_ids = [chat_id]

    fc = FlyoneClient()

    directions_by_chats = await DataAccessLayer.get_directions_by_chats(callee_chat_ids)

    to_fetch = []

    async with redis_client() as cache:

        for chat, directions in directions_by_chats.items():
            for direction in directions:
                travel_date = direction.travel_date.isoformat()

                src = direction.src
                dst = direction.dst

                msg_header = (
                    f'From: {src} 🛫\n'
                    f'To: {dst} 🛬\n'
                    f'Price limit: {direction.price} 💶\n'
                    f'Travel date: {direction.travel_date.strftime("%d.%m.%Y")} 🧳'
                )

                notifier = TgBotNotifier(
                    chat_id=chat.tg_id, price_limit=Decimal(direction.price), msg_header=msg_header
                )

                to_fetch.append(fetch_flights(src, dst, travel_date, msg_header, notifier, cache, fc))

    msgs_by_notifier: dict[TgBotNotifier, list[str]] = defaultdict(list)

    for result in await asyncio.gather(*to_fetch):

        if result is None:
            continue

        forward, backward, notifier = result

        forward_msg, backward_msg = await asyncio.gather(
            notifier.form_msg(forward),
            notifier.form_msg(backward)
        )

        msg = (
            f'Forward flights ✈️:\n{forward_msg}\n\n'
            f'Backward flights 🛩️:\n{backward_msg}'
        )

        msgs_by_notifier[notifier].append(msg)

    await asyncio.gather(*[notifier.send_msgs(msgs) for notifier, msgs in msgs_by_notifier.items()])


if __name__ == '__main__':
    # TODO make separate archives for trigger and bot
    # TODO refactor DAL
    # TODO add bot buttons
    # TODO add api
    # TODO add tests
    asyncio.run(main())
