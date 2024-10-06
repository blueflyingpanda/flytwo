import asyncio
from decimal import Decimal
from os import environ

import aiohttp

from client import FlyoneClient, Flight

BOT_TOKEN = environ.get('BOT_TOKEN')

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

    async def send_msg(self, msg: str):
        payload = {'text': f'{msg}'}

        for chat_id in self.chat_ids:
            payload['chat_id'] = chat_id

            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=payload, ssl=False) as response:
                    print(await response.json())


async def main():
    fc = FlyoneClient()

    result = await fc.get_flights(
        dep='RMO', arr='EVN', dep_date='2024-10-30', arr_date='2024-10-30', currency='EUR'
    )

    forward, backward = result

    chat_ids = environ.get('CHAT_IDS').split(',')
    price_limit = Decimal(environ.get('PRICE_LIMIT'))

    notifier = TgBotNotifier(chat_ids=chat_ids, price_limit=price_limit)

    msg = await notifier.form_msg(forward)

    await notifier.send_msg(f'Forward flights:\n{msg}')

    if msg:
        msg = await notifier.form_msg(backward)
        await notifier.send_msg(f'Backward flights:\n{msg}')

    await notifier.send_msg(f'Price limit: {notifier.price_limit} EUR')


if __name__ == '__main__':
    asyncio.run(main())
