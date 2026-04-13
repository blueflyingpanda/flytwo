import asyncio
import random
from decimal import Decimal

import aiohttp
from pycountry import countries

from client.client import Flight
from conf import BOT_TOKEN
from logs import custom_logger

if False:
    import db


class TgBotNotifier:
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    max_msg_len = 4096

    def __init__(self, chat_id: int, price_limit: Decimal | None = None, msg_header: str = ''):
        self.chat_id = chat_id
        self.price_limit = price_limit
        self.msg_header = msg_header

    def __hash__(self) -> int:
        return hash(self.chat_id)

    async def form_msg(self, flights: list[Flight]) -> str:

        msgs = []
        flights = [flight for flight in flights if self.price_limit is None or flight.price <= self.price_limit]

        min_price = max_price = None
        prices = [flight.price for flight in flights]

        if prices:
            min_price = min(prices)
            max_price = max(prices)

            if min_price == max_price:
                min_price = max_price = None

        for flight in flights:
            day, month, year = flight.travel_date.split('.')
            f_date = f'{day.zfill(2)}.{month.zfill(2)}.{year}'

            price = f'{flight.price}'

            msg = f'{f_date}: {price.rjust(3)}{flight.currency_symbol}'

            if flight.price == min_price:
                msg = f'{msg} ✅'
            elif flight.price == max_price:
                msg = f'{msg} ❌'
            else:
                msg = f'{msg}   '

            prev_price = f'{flight.prev_price or ""}'

            if prev_price:
                diff = flight.price - flight.prev_price
                if diff > 0:
                    arrow = '⬆️'
                else:
                    arrow = '⬇️'
                    diff = -diff

                diff_str = f'{arrow}{str(diff).rjust(3)}{flight.currency_symbol}'
                msg = f'{msg} {diff_str} (was {prev_price.rjust(3)}{flight.currency_symbol})'

            msgs.append(msg)

        return '\n'.join(msgs) or 'not found 🥲'

    async def send_msgs(self, msgs: list[str]):

        async def slow_send(data: dict):
            """fixes connection timeout to https://api.telegram.org"""
            await asyncio.sleep(random.uniform(0.1, 1.0))
            resp = await session.post(self.url, json=data, ssl=False)
            custom_logger.info(await resp.text())

        async with aiohttp.ClientSession() as session:
            to_send = []

            for msg in msgs:
                payload = {
                    'text': f'<pre>{self.msg_header}\n\n{msg}</pre>',
                    'chat_id': self.chat_id,
                    'parse_mode': 'HTML',
                }
                to_send.append(slow_send(payload))

            await asyncio.gather(*to_send)

    @staticmethod
    async def form_err(msg: str) -> str:
        warn = '⚠️'
        left, sep, right = msg.partition(':')
        err_msg = (right if sep else left).strip()

        return f'{warn} {err_msg} {warn}'

    async def send_err(self, msg: str):
        err_msg = await self.form_err(msg)

        await self.send_msgs([err_msg])

    @staticmethod
    async def form_direction_info(direction: 'db.Direction', airport_by_code: dict) -> str:
        src = direction.src
        dst = direction.dst

        src_flag = dst_flag = ''

        try:
            src_country = countries.lookup(airport_by_code[src].country)
        except (LookupError, KeyError):
            src_country = None
        try:
            dst_country = countries.lookup(airport_by_code[dst].country)
        except (LookupError, KeyError):
            dst_country = None

        if src_country is not None:
            src_flag = src_country.flag
        if dst_country is not None:
            dst_flag = dst_country.flag

        return (
            f'From: {src} {src_flag}\n'
            f'To: {dst} {dst_flag}\n'
            f'Price limit: {direction.price} 💶\n'
            f'Travel date: {direction.travel_date.strftime("%d.%m.%Y")} ✈️'
        )
