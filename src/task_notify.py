import asyncio
import json
from collections import defaultdict
from decimal import Decimal
from itertools import chain

from cache import redis_client
from change_detector import FlightsChangeDetector
from dal import DataAccessLayer
from fetcher import FlightsFetcher
from fly_client.client import FlyoneClient, Flight
from notifier import TgBotNotifier


async def main(event: dict | None = None, context=None):
    callee_chat_ids = None
    display_all = False

    if event is not None and (body := event.get('body')):
        body = json.loads(body)
        chat_id = body.get('chat_id')
        if chat_id is not None:
            callee_chat_ids = [chat_id]
            chat = await DataAccessLayer.get_chat(tg_id=chat_id)

            if chat:
                display_all = not chat.less


    fc = FlyoneClient()
    airport_by_code = await fc.airport_by_code

    directions_by_chats = await DataAccessLayer.get_directions_by_chats(callee_chat_ids)

    to_fetch = []

    async with redis_client() as cache:

        for chat, directions in directions_by_chats.items():
            for direction in directions:

                msg_header = await TgBotNotifier.form_direction_info(direction, airport_by_code)

                notifier = TgBotNotifier(
                    chat_id=chat.tg_id, price_limit=Decimal(direction.price), msg_header=msg_header
                )

                to_fetch.append(FlightsFetcher.fetch_flights(direction, notifier, cache, fc))

    msgs_by_notifier: dict[TgBotNotifier, list[str]] = defaultdict(list)

    results = await asyncio.gather(*to_fetch)
    results = [result for result in results if result is not None]

    fetched_flights: list[Flight] = []

    for result in results:
        forwards, backwards, _ = result

        fetched_flights.extend(forwards)
        fetched_flights.extend(backwards)

    changed_flights: set[Flight] = set(await FlightsChangeDetector.get_changed_flights(fetched_flights))

    for result in results:

        forwards, backwards, notifier = result

        flights = chain(forwards, backwards)

        flights = (flight for flight in flights if notifier.price_limit is None or flight.price <= notifier.price_limit)

        if display_all or any(flight in changed_flights for flight in flights):

            forward_msg, backward_msg = await asyncio.gather(
                notifier.form_msg(forwards),
                notifier.form_msg(backwards)
            )

            msg = (
                f'Forward flights 🛫:\n{forward_msg}\n\n'
                f'Backward flights 🛬:\n{backward_msg}'
            ).replace(' EUR', '€')

            msgs_by_notifier[notifier].append(msg)

    await asyncio.gather(*[notifier.send_msgs(msgs) for notifier, msgs in msgs_by_notifier.items()])


if __name__ == '__main__':
    asyncio.run(main())