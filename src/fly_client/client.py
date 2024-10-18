from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import aiohttp
from pydantic import TypeAdapter, BaseModel


class Direction(Enum):
    FORWARD = 1
    BACKWARD = 2


class Airport(BaseModel):
    code: str = ''
    name: str = ''
    country: str = ''


class Flight(BaseModel):
    from_airport: Airport
    to_airport: Airport
    travel_date: str
    currency: str
    price: Decimal


FLIGHTS_TYPE_ADAPTER = TypeAdapter(list[Flight])


class FlyoneException(Exception):
    """Base exception for all Flyone client exceptions."""


class FlyoneClient:

    view_url = 'https://bookings.flyone.eu/FareView'
    api_url = 'https://api2.flyone.eu/api'
    ssl = False

    default_currency = 'EUR'

    def __init__(self):
        self._token: str = ''
        self._airports_by_code: dict[str, 'Airport'] = {}

    async def refresh_token(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.view_url, ssl=self.ssl) as response:
                self._token = response.cookies.get('COOKIE_TOKEN').value

    @property
    async def token(self):
        if not self._token:
            await self.refresh_token()
        return self._token

    async def request(self, path: str, data: dict | list, retry: bool = False) -> dict[str, Any]:
        token = await self.token

        headers = {'Authorization': f'Bearer {token}'}
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.api_url}/{path}', json=data, headers=headers, ssl=self.ssl) as response:
                if response.status != 200:
                    if response.status == 401 and not retry:
                        await self.refresh_token()
                        return await self.request(path, data, retry=True)
                    else:
                        raise FlyoneException(f'{response.status}: {await response.text()}')

                response_data = (await response.json())

                result = response_data['result']

                if not result['isSuccess']:
                    msgs = result['msgs']
                    raise FlyoneException('\n'.join(( f'{msg["code"]}: {msg["msgText"]}' for msg in msgs)))

                return response_data

    @property
    async def airport_by_code(self) -> dict[str, 'Airport']:
        if not self._airports_by_code:
            result: dict[str, Airport] = {}
            response = await self.request('Routes/get-routes', {})

            for route in response['routes']:
                code = route['depCode']
                result[code] = Airport(code=code, name=route['depAirportName'], country=route['countryName'])

            self._airports_by_code = result

        return self._airports_by_code

    async def get_fare_stats(self, *, dep: str, travel_date: str = '', currency: str = '') -> dict[str, Any]:
        payload = {
            'origin': dep,
            'travelDate': travel_date or datetime.now().strftime('%Y-%m-%d'),
            'currencyCode': currency or self.default_currency,
        }
        return await self.request('search/get-route-fare', payload)

    async def get_flights(
            self,
            *,
            dep: str, arr: str, dep_date: str, arr_date: str,
            currency: str = '', before: int = 16, after: int = 16, passengers: int = 1
    ) -> tuple[list[Flight], list[Flight]]:
        """before/after window must not exceed 32 days"""
        payload = {
            'reservationType': 1,
            'searchCriteria': {
                'journeyInfo': {
                    'journeyType': 2,
                    'routeInfo': [
                        {
                            'depCity': dep,
                            'arrCity': arr,
                            'travelDate': dep_date,
                            'schedule': {
                                'before': before,
                                'after': after
                            }
                        },
                        {
                            'depCity': arr,
                            'arrCity': dep,
                            'travelDate': arr_date,
                            'schedule': {
                                'before': before,
                                'after': after
                            }
                        }
                    ]
                },
                'paxInfo': [{'paxKey': f'Adult{n}', 'paxType': 1} for n in range(1, passengers + 1)],
            },
            'ipAddress': '8.8.8.8',  # required by server - for anonymity uses google dns ip address
            'currencyCode': currency or self.default_currency,
        }

        result = await self.request('search/schedule-flights', payload)

        flights_forwards: list[Flight] = []
        flights_backward: list[Flight] = []

        airport_by_code = await self.airport_by_code
        dep_airport: Airport = airport_by_code[dep]
        arr_airport: Airport = airport_by_code[arr]

        for direction in result['flightSchedule']:
            is_back = direction['direction'] == Direction.BACKWARD
            days = []
            year = direction['year']

            for month in direction['month']:
                month_num = month['month']
                days.extend(
                    [
                        Flight(
                            from_airport=arr_airport if is_back else dep_airport,
                            to_airport=dep_airport if is_back else arr_airport,
                            travel_date=f'{day["date"]}.{month_num}.{year}',
                            currency=currency,
                            price=Decimal(day["price"])
                        )
                        for day in month['days'] if day['isFlightAvailable']]
                )

            if is_back:
                flights_backward = days
            else:
                flights_forwards = days

        return flights_forwards, flights_backward
