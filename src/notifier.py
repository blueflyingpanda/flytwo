import asyncio
import random
from decimal import Decimal

import aiohttp
from pycountry import countries

import db
from conf import BOT_TOKEN
from fly_client.client import Flight


class TgBotNotifier:

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    max_msg_len = 4096

    def __init__(self, chat_id: int, price_limit: Decimal | None = None, msg_header: str = ''):
        self.chat_id = chat_id
        self.price_limit = price_limit
        self.msg_header = msg_header

    def __hash__(self) -> int:
        return hash(self.chat_id)

    @staticmethod
    async def form_msg(flights: list[Flight]):

        msgs = []

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

            msg = f'{f_date}: {flight.from_airport.code} -> {flight.to_airport.code} - {price.rjust(4)} {flight.currency}'

            if flight.price == min_price:
                msg = f'{msg} ✅'
            elif flight.price == max_price:
                msg = f'{msg} ❌'

            msgs.append(msg)

        return '\n'.join(msgs) or 'not found 🥲'

    async def send_msgs(self, msgs: list[str]):

        async def slow_send(data: dict):
            """fixes connection timeout to https://api.telegram.org"""
            await asyncio.sleep(random.uniform(0.1, 1.0))
            await session.post(self.url, json=data, ssl=False)

        async with aiohttp.ClientSession() as session:
            to_send = []

            for msg in msgs:
                payload = {'text': f'{self.msg_header}\n\n{msg}', 'chat_id': self.chat_id}
                to_send.append(slow_send(payload))

            await asyncio.gather(*to_send)

    async def send_err(self, msg: str):
        warn = '⚠️'
        err_msg = msg.partition(":")[2].strip()
        await self.send_msgs([f'{warn} {err_msg} {warn}'.strip()])

    @staticmethod
    async def form_direction_info(direction: db.Direction, airport_by_code: dict) -> str:
        src = direction.src
        dst = direction.dst

        src_flag = dst_flag = ''

        try:
            src_country = countries.lookup(airport_by_code.get(src).country)
        except LookupError:
            src_country = None
        try:
            dst_country = countries.lookup(airport_by_code.get(dst).country)
        except LookupError:
            dst_country = None

        if src_country is not None:
            src_flag = src_country.flag  # noqa
        if dst_country is not None:
            dst_flag = dst_country.flag  # noqa

        return (
            f'From: {src} {src_flag}\n'
            f'To: {dst} {dst_flag}\n'
            f'Price limit: {direction.price} 💶\n'
            f'Travel date: {direction.travel_date.strftime("%d.%m.%Y")} ✈️'
        )
