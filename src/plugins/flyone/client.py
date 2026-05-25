from decimal import Decimal
from typing import Any

import aiohttp

from client import Airport, BaseClient, ClientError, Direction, FareStats, Flight


class FlyoneClient(BaseClient):
    api_url = 'https://api2.flyone.eu/api'

    view_url = 'https://bookings.flyone.eu/FareView'
    ssl = False

    async def _refresh_token(self):
        async with aiohttp.ClientSession() as session, session.get(self.view_url, ssl=self.ssl) as response:
            self._token = response.cookies.get('COOKIE_TOKEN').value

    async def _request(self, path: str, data: dict | list, is_retry: bool = False) -> dict[str, Any]:
        token = await self._get_token()

        headers = {'Authorization': f'Bearer {token}'}
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{self.api_url}/{path}', json=data, headers=headers, ssl=self.ssl) as response:
                if response.status != 200:
                    if response.status == 401 and not is_retry:
                        await self._refresh_token()
                        return await self._request(path, data, is_retry=True)
                    else:
                        raise ClientError(f'{response.status}: {await response.text()}')

                response_data = await response.json()

                result = response_data['result']

                if not result['isSuccess']:
                    msgs = result['msgs']
                    raise ClientError('\n'.join(f'{msg["code"]}: {msg["msgText"]}' for msg in msgs))

                return response_data

    async def airport_by_code(self) -> dict[str, 'Airport']:
        if not self._airports_by_code:
            result: dict[str, Airport] = {}
            response = await self._request('Routes/get-routes', {})

            for route in response['routes']:
                code = route['depCode']
                result[code] = Airport(code=code, name=route['depAirportName'], country=route['countryName'])

            self._airports_by_code = result

        return self._airports_by_code

    async def get_flights(
        self,
        *,
        dep: str,
        arr: str,
        dep_date: str,
        arr_date: str,
        currency: str,
        before: int = 10,
        after: int = 10,
        passengers: int = 1,
    ) -> tuple[list[Flight], list[Flight]]:
        """before/after window must not exceed 20 days"""
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
                            'schedule': {'before': before, 'after': after},
                        },
                        {
                            'depCity': arr,
                            'arrCity': dep,
                            'travelDate': arr_date,
                            'schedule': {'before': before, 'after': after},
                        },
                    ],
                },
                'paxInfo': [{'paxKey': f'Adult{n}', 'paxType': 1} for n in range(1, passengers + 1)],
            },
            'ipAddress': '8.8.8.8',  # required by server - for anonymity uses google dns ip address
            'currencyCode': currency,
        }

        result = await self._request('search/schedule-flights', payload)

        flights_forwards: list[Flight] = []
        flights_backward: list[Flight] = []

        airport_by_code = await self.airport_by_code()
        dep_airport: Airport = airport_by_code[dep]
        arr_airport: Airport = airport_by_code[arr]

        for direction in result['flightSchedule']:
            is_back = direction['direction'] == Direction.BACKWARD.value
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
                            price=Decimal(day['price']),
                            airline='flyone',
                        )
                        for day in month['days']
                        if day['isFlightAvailable'] and not day['isSoldOut']
                    ]
                )

            if is_back:
                flights_backward = days
            else:
                flights_forwards = days

        return flights_forwards, flights_backward

    async def get_fare_stats(self, *, dep: str, travel_date: str, currency: str) -> FareStats:
        payload = {
            'origin': dep,
            'travelDate': travel_date,
            'currencyCode': currency,
        }
        response = await self._request('search/get-route-fare', payload)
        return FareStats.model_validate(response)
