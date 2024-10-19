import asyncio
import json
from decimal import Decimal

import aiohttp
from pydantic_core import to_jsonable_python

from cache import redis_client
from dal import DataAccessLayer
from fly_client.client import FlyoneClient, Flight, FlyoneException, FLIGHTS_TYPE_ADAPTER
from conf import BOT_TOKEN, REDIS_TTL
from logs import custom_logger


class TgBotNotifier:

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    max_msg_len = 4096

    def __init__(self, chat_id: int, price_limit: Decimal | None):
        self.chat_id = chat_id
        self.price_limit = price_limit

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


    async def send_msg(self, msg: str):

        payload = {'text': f'{msg}', 'chat_id': self.chat_id}

        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=payload, ssl=False):
                pass

    async def send_err(self, msg: str, header: str = ''):
        warn = '⚠️'
        err_msg = msg.partition(":")[2].strip()
        await self.send_msg(f'{header}\n\n{warn} {err_msg} {warn}'.strip())


async def main(event: dict | None = None, context=None):
    callee_chat_ids = None

    if event is not None and (body := event.get('body')):
        body = json.loads(body)
        chat_id = body.get('chat_id')
        if chat_id is not None:
            callee_chat_ids = [chat_id]

    fc = FlyoneClient()

    directions_by_chats = await DataAccessLayer.get_directions_by_chats(callee_chat_ids)

    async with redis_client() as cache:

        for chat, directions in directions_by_chats.items():
            for direction in directions:
                travel_date = direction.travel_date.isoformat()
                src = direction.src
                dst = direction.dst

                notifier = TgBotNotifier(chat_id=chat.tg_id, price_limit=Decimal(direction.price))

                msg_header = (
                    f'From: {src}\n'
                    f'To: {dst}\n'
                    f'Price limit: {direction.price} EUR\n'
                    f'Travel date: {travel_date}'
                )

                forward_value = backward_value = None

                if REDIS_TTL is not None:
                    forward_key = f'{src}{dst}{travel_date.replace("-", "")}'
                    backward_key = f'{dst}{src}{travel_date.replace("-", "")}'

                    forward_value = await cache.get(forward_key)
                    backward_value = await cache.get(backward_key)

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
                        await notifier.send_err(err_msg, msg_header)
                        continue

                    if REDIS_TTL is not None:
                        await cache.set(forward_key, json.dumps(forward, default=to_jsonable_python), ex=REDIS_TTL)
                        await cache.set(backward_key, json.dumps(backward, default=to_jsonable_python), ex=REDIS_TTL)
                else:
                    custom_logger.info(f'Cache found: {src} -> {dst}')

                    forward: list[Flight] = FLIGHTS_TYPE_ADAPTER.validate_json(forward_value)
                    backward: list[Flight] = FLIGHTS_TYPE_ADAPTER.validate_json(backward_value)

                forward_msg = await notifier.form_msg(forward)
                backward_msg = await notifier.form_msg(backward)

                msg = (
                    f'{msg_header}\n\n'
                    f'Forward flights:\n{forward_msg}\n\n'
                    f'Backward flights:\n{backward_msg}'
                )

                await notifier.send_msg(msg)


if __name__ == '__main__':
    # TODO optimise and profile
    # TODO improve ui
    # TODO make separate archives for trigger and bot
    # TODO add tests
    asyncio.run(main())
