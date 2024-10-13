import asyncio
import hashlib
from decimal import Decimal
from os import environ

import aiohttp

from fly_client.client import FlyoneClient, Flight
from conf import BOT_TOKEN


class TgBotNotifier:

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'

    def __init__(self, chat_ids: list[str], price_limit: Decimal | None):
        self.chat_ids = chat_ids
        self.price_limit = price_limit

    async def form_msg(self, flights: list[Flight]):

        msgs = []
        flights = [flight for flight in flights if self.price_limit is None or flight.price <= self.price_limit]

        for flight in flights:
            day, month, year = flight.travel_date.split('.')
            f_date = f'{day.zfill(2)}.{month}.{year}'

            price = f'{flight.price}'

            msg = f'{f_date}: {flight.from_airport.code} -> {flight.to_airport.code} - {price.rjust(4)} {flight.currency}'

            msgs.append(msg)

        return '\n'.join(msgs) or 'not found 🥲'

    async def _get_hash(self, msg: str) -> str:
        # Create a new sha256 hash object
        msg_hash = hashlib.sha256()
        msg_hash.update(msg.encode())

        return msg_hash.hexdigest()

    async def _check_sent(self, msg: str) -> bool:
        # TODO DB to store chat subscriptions
        # TODO not send msg that already been sent by storing msg_hash in DIRECTIONS and comparing Forward flights msg hash with the one in db
        return self._get_hash(msg) in set()

    async def send_msg(self, msg: str, no_repeat: bool = False) -> bool:

        if no_repeat:
            if await self._check_sent(msg):
                return False
            else:
                # TODO update msg_hash
                pass

        payload = {'text': f'{msg}'}

        for chat_id in self.chat_ids:
            payload['chat_id'] = chat_id

            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload, ssl=False) as response:
                    print(await response.json())

        return True


async def main(*args, **kwargs):
    fc = FlyoneClient()

    travel_date = environ.get('TRAVEL_DATE')

    result = await fc.get_flights(
        dep=environ.get('ORIGIN'),
        arr=environ.get('DESTINATION'),
        dep_date=travel_date,
        arr_date=travel_date,
        currency='EUR'
    )

    forward, backward = result

    chat_ids = environ.get('CHAT_IDS').split(',')
    price_limit = Decimal(environ.get('PRICE_LIMIT'))

    notifier = TgBotNotifier(chat_ids=chat_ids, price_limit=price_limit)

    msg = await notifier.form_msg(forward)

    sent = await notifier.send_msg(f'Forward flights:\n{msg}', no_repeat=True)

    if sent:
        msg = await notifier.form_msg(backward)
        await notifier.send_msg(f'Backward flights:\n{msg}')

        await notifier.send_msg(f'Price limit: {price_limit} EUR\nTravel date: {travel_date}')


if __name__ == '__main__':
    asyncio.run(main())
