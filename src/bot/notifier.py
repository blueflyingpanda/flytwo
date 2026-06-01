import asyncio
import random
from datetime import datetime
from decimal import Decimal

import aiohttp
from pycountry import countries

from cache import redis_client
from client import Airport, DestinationFare, Flight
from conf import BOT_TOKEN
from currency_converter import CurrencyConverter
from logs import logger

if False:
    import db


class TgBotNotifier:
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    max_msg_len = 4096

    def __init__(
        self,
        chat_id: int,
        price_limit: Decimal | None = None,
        msg_header: str = '',
        notify_on_decrease: bool | None = None,
        threshold: int = 0,
        currency: str = 'EUR',
    ):
        self.chat_id = chat_id
        self.price_limit = price_limit
        self.msg_header = msg_header
        self.notify_on_decrease = notify_on_decrease
        self.threshold = threshold
        self.currency = currency

    def __hash__(self) -> int:
        return hash(self.chat_id)

    @staticmethod
    def _get_min_max_price(flights: list[Flight]) -> tuple[Decimal | None, Decimal | None]:
        min_price = max_price = None
        prices = [flight.price for flight in flights]

        if prices:
            min_price = min(prices)
            max_price = max(prices)

            if min_price == max_price:
                min_price = max_price = None

        return min_price, max_price

    @property
    def currency_symbol(self) -> str:
        return CurrencyConverter.CURRENCY_SYMBOLS.get(self.currency, self.currency)

    async def convert_prices(self, flights: list[Flight]) -> list[Flight]:

        async def convert(flight: Flight) -> Flight:
            flight.price = round(await currency_converter.convert(flight.price, flight.currency, self.currency))
            if flight.prev_price is not None:
                flight.prev_price = round(
                    await currency_converter.convert(flight.prev_price, flight.currency, self.currency)
                )
            return flight

        async with aiohttp.ClientSession() as session, redis_client() as cache:
            currency_converter = CurrencyConverter(session, cache)

            tasks = [convert(flight) for flight in flights]
            return await asyncio.gather(*tasks)

    async def form_msg(self, flights: list[Flight]) -> str:

        msgs = []
        flights = await self.convert_prices(flights)
        flights = [flight for flight in flights if self.price_limit is None or flight.price <= self.price_limit]

        min_price, max_price = self._get_min_max_price(flights)

        for flight in flights:
            day, month, year = str(flight.travel_date.day), str(flight.travel_date.month), str(flight.travel_date.year)
            f_date = f'{day.zfill(2)}.{month.zfill(2)}.{year}'

            price = f'{flight.price}'

            msg = f'{f_date}: {price.rjust(3)}{self.currency_symbol} [{flight.airline}]'

            if flight.price == min_price:
                msg = f'{msg} ✅'
            elif flight.price == max_price:
                msg = f'{msg} ❌'
            else:
                msg = f'{msg}'

            prev_price = f'{flight.prev_price or ""}'

            if prev_price:
                diff = flight.price - flight.prev_price
                if diff > 0:
                    arrow = '⬆️'
                else:
                    arrow = '⬇️'
                    diff = -diff

                diff_str = f'{arrow}{str(diff).rjust(3)}{self.currency_symbol}'
                msg = f'{msg} {diff_str} (was {prev_price.rjust(3)}{self.currency_symbol})'

            msgs.append(msg)

        return '\n'.join(msgs) or 'not found 🥲'

    async def send_msgs(self, msgs: list[str]):

        async def slow_send(data: dict):
            """fixes connection timeout to https://api.telegram.org"""
            await asyncio.sleep(random.uniform(0.1, 1.0))
            resp = await session.post(self.url, json=data, ssl=False)
            logger.info(await resp.text())

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
    def get_country_flag(airport: str, airport_by_code) -> str:
        flag = ''

        try:
            country = countries.lookup(airport_by_code[airport].country)
        except (LookupError, KeyError):
            country = None

        if country is not None:
            flag = country.flag

        return flag

    @classmethod
    async def form_fare_info(
        cls, src: str, fare: DestinationFare, airport_by_code: dict[str, Airport], currency: str, travel_date: datetime
    ) -> str:
        dst = fare.destination

        src_flag = cls.get_country_flag(src, airport_by_code)
        dst_flag = cls.get_country_flag(dst, airport_by_code)

        price = fare.price
        fare_currency = fare.currency

        async with aiohttp.ClientSession() as session, redis_client() as cache:
            currency_converter = CurrencyConverter(session, cache)
            converted_price = await currency_converter.convert(Decimal(price), fare_currency, currency)

        return (
            f'From: {src} {src_flag}\n'
            f'To: {dst} {dst_flag}\n'
            f'Price: {converted_price} {currency}\n'
            f'Travel date: {travel_date.strftime("%d.%m.%Y")} ✈️\n'
        )

    @classmethod
    async def form_direction_info(cls, direction: 'db.Direction', airport_by_code: dict, currency: str) -> str:
        src = direction.src
        dst = direction.dst

        src_flag = cls.get_country_flag(src, airport_by_code)
        dst_flag = cls.get_country_flag(dst, airport_by_code)

        if direction.notify_on_decrease is None:
            notify_on = '↕️'
        else:
            notify_on = '⬇️' if direction.notify_on_decrease else '⬆️'

        return (
            f'From: {src} {src_flag}\n'
            f'To: {dst} {dst_flag}\n'
            f'Price limit: {direction.price} {currency}\n'
            f'Travel date: {direction.travel_date.strftime("%d.%m.%Y")} ✈️\n'
            f'Notify on: {notify_on}\n'
            f'Threshold: {direction.threshold} 🪙'
        )
