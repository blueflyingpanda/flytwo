from decimal import Decimal

import db
from dal import DataAccessLayer
from fly_client.client import Flight


class FlightsChangeDetector:

    @staticmethod
    async def get_changed_flights(
            fetched_flights: list[Flight],
            manual: bool = False,
    ):
        flights: list[db.Flight] = await DataAccessLayer.get_flights(fetched_flights)
        stored_flights: dict[db.Flight, db.Flight] = {flight: flight for flight in flights}

        changed_flights: list[Flight] = []
        updated_price_by_flight: list[dict[str, int]] = []

        for flight in fetched_flights:

            if stored_flight := stored_flights.get(flight):
                if stored_flight.price != int(flight.price):
                    updated_price_by_flight.append({
                        'id': stored_flight.id,
                        'price': int(flight.price)
                    })

                    flight.prev_price = Decimal(stored_flight.price)  # noqa
                    changed_flights.append(flight)

        if updated_price_by_flight and not manual:
            await DataAccessLayer.update_flights(updated_price_by_flight)

        return changed_flights
