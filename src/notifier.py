import asyncio
import json
from decimal import Decimal

import aiohttp

from dal import DataAccessLayer
from fly_client.client import FlyoneClient, Flight, FlyoneException
from conf import BOT_TOKEN


class TgBotNotifier:

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'

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

    async def send_err(self, msg: str):
        warn = '⚠️'
        err_msg = msg.partition(":")[2].strip()
        await self.send_msg(f'{warn} {err_msg} {warn}')


async def main(event: dict | None = None, context=None):
    callee_chat_ids = None

    if event is not None and (body := event.get('body')):
        body = json.loads(body)
        chat_id = body.get('chat_id')
        if chat_id is not None:
            callee_chat_ids = [chat_id]

    fc = FlyoneClient()

    directions_by_chats = await DataAccessLayer.get_directions_by_chats(callee_chat_ids)

    for chat, directions in directions_by_chats.items():
        for direction in directions:
            travel_date = direction.travel_date.isoformat()
            src = direction.src
            dst = direction.dst

            notifier = TgBotNotifier(chat_id=chat.tg_id, price_limit=Decimal(direction.price))

            await notifier.send_msg(
                f'From: {src}\n'
                f'To: {dst}\n'
                f'Price limit: {direction.price} EUR\n'
                f'Travel date: {travel_date}'
            )

            try:
                result = await fc.get_flights(
                    dep=src,
                    arr=dst,
                    dep_date=travel_date,
                    arr_date=travel_date,
                    currency='EUR'
                )
            except FlyoneException as e:
                await notifier.send_err(f'{e}')
                continue

            forward, backward = result

            msg = await notifier.form_msg(forward)
            await notifier.send_msg(f'Forward flights:\n{msg}')

            msg = await notifier.form_msg(backward)
            await notifier.send_msg(f'Backward flights:\n{msg}')


if __name__ == '__main__':
    # TODO add caching
    asyncio.run(main())
