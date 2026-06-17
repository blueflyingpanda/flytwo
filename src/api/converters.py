from decimal import Decimal

import aiohttp

from api.validators import validate_currency
from cache import redis_client
from currency_converter import CurrencyConverter
from dal import FlightKey, PricePoint


async def convert_currency(amount: int, from_cur: str, to_cur: str) -> int:
    from_cur = validate_currency(from_cur)
    to_cur = validate_currency(to_cur)
    async with aiohttp.ClientSession() as session, redis_client() as cache:
        converter = CurrencyConverter(session, cache)
        result = await converter.convert(Decimal(amount), from_cur, to_cur)
    return round(result)


async def convert_price_history(
    price_history: dict[FlightKey, list[PricePoint]], to_currency: str
) -> dict[FlightKey, list[PricePoint]]:
    async with aiohttp.ClientSession() as session, redis_client() as cache:
        converter = CurrencyConverter(session, cache)

        converted: dict[FlightKey, list[PricePoint]] = {}
        for key, points in price_history.items():
            new_points = [
                PricePoint(
                    price=round(await converter.convert(Decimal(p.price), key.currency, to_currency)),
                    dt=p.dt,
                )
                for p in points
            ]
            converted[FlightKey(airline=key.airline, travel_date=key.travel_date, currency=to_currency)] = new_points

    return converted
