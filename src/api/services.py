import asyncio
import logging
from datetime import date
from typing import NamedTuple

import aiohttp

from api.common import bad_request
from api.models import PromoFare
from api.validators import validate_airport_code
from cache import redis_client
from client import Airport, DestinationFare, FareStats
from currency_converter import CurrencyConverter
from dal import DataAccessLayer
from db import Chat
from dispatcher import dispatcher


class ResolvedDirection(NamedTuple):
    src: str
    dst: str
    travel_date: date | None


class DirectionManager:
    FREE_LIMIT = 5
    PREMIUM_LIMIT = 10

    def __init__(self, chat: Chat) -> None:
        self.chat = chat

    async def resolve(
        self,
        *,
        link: str | None,
        src: str | None,
        dst: str | None,
        travel_date: date | None,
    ) -> ResolvedDirection:
        if link:
            parser = dispatcher.pick_parser(link)
            if parser is None:
                raise bad_request('Unrecognized link. Use a supported airline URL or enter airports manually.')
            parsed_src, parsed_dst, travel_date_str = parser.parse()
            from datetime import datetime

            src, dst = parsed_src, parsed_dst
            travel_date = datetime.strptime(travel_date_str, '%d.%m.%Y').date()

        if not src or not dst:
            raise bad_request('Both src and dst are required.')

        src = validate_airport_code(src)
        dst = validate_airport_code(dst)

        if src == dst:
            raise bad_request('Source cannot be the same as destination.')

        return ResolvedDirection(src, dst, travel_date)

    async def add(self, *, src: str, dst: str, travel_date: date, price: int) -> bool:
        """Create or update a direction. Returns True when newly created."""
        airport_by_code = await dispatcher.get_airport_by_code()
        if src not in airport_by_code or dst not in airport_by_code:
            raise bad_request('Airport not supported. See the airports list.')

        directions_by_chats = await DataAccessLayer.get_directions_by_chats([self.chat.tg_id])
        _, directions = next(iter(directions_by_chats.items()))

        is_new = not any(d.src == src and d.dst == dst for d in directions)
        limit = self.PREMIUM_LIMIT if self.chat.premium else self.FREE_LIMIT

        if is_new and len(directions) >= limit:
            detail = f'You have reached the limit of {limit} active directions.'
            if not self.chat.premium:
                detail += ' Remove one or upgrade to premium.'
            raise bad_request(detail)

        _, created = await DataAccessLayer.create_direction(
            chat_id=self.chat.id, src=src, dst=dst, travel_date=travel_date, price=price
        )
        return created

    async def find_promo_fares(self, *, src: str, travel_date: date, price: int) -> list[PromoFare]:
        airport_by_code: dict[str, Airport] = await dispatcher.get_airport_by_code()
        src = validate_airport_code(src)
        if src not in airport_by_code:
            raise bad_request(f'Unsupported airport: {src}')

        limit = self.PREMIUM_LIMIT if self.chat.premium else self.FREE_LIMIT

        async def process_client(client_cls) -> FareStats:
            return await client_cls().get_fare_stats(
                dep=src, travel_date=f'{travel_date:%Y-%m-%d}', currency=self.chat.currency
            )

        tasks = [process_client(cls) for cls in dispatcher.get_client_classes()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        responses: list[FareStats] = []
        for result in results:
            if isinstance(result, Exception):
                logging.exception('promo fare fetch failed', exc_info=result)
                continue
            responses.append(result)

        async with aiohttp.ClientSession() as session, redis_client() as cache:
            converter = CurrencyConverter(session, cache)

            fares: list[tuple[int, DestinationFare]] = []
            for response in responses:
                for fare in response.destinationFares:
                    converted = round(await converter.convert(fare.price, fare.currency, self.chat.currency))
                    if converted <= price:
                        fares.append((converted, fare))

        fares.sort(key=lambda x: x[0])

        return [
            PromoFare(
                src=src,
                dst=fare.destination,
                price=converted,
                currency=self.chat.currency,
                airline=fare.airline,
                travel_date=travel_date,
            )
            for converted, fare in fares[:limit]
        ]
