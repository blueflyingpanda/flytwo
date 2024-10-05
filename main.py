import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pprint import pprint
from typing import Any

import aiohttp
import click


@dataclass
class Airport:
    code: str = ''
    name: str = ''
    country: str = ''


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
                        raise Exception(f'{response.status}: {await response.text()}')

                response_data = (await response.json())

                result = response_data['result']

                if not result['isSuccess']:
                    raise Exception(f'{result['code']}: {result['msgText']}')

                return response_data

    @property
    async def airport_by_code(self) -> dict[str, 'Airport']:
        if not self._airports_by_code:
            result: dict[str, 'Airport'] = {}
            response = await self.request('Routes/get-routes', {})

            for route in response['routes']:
                code = route['depCode']
                result[code] = Airport(code, route['depAirportName'], route['countryName'])

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
            currency: str = '', before: int = 10, after: int = 10, passengers: int = 1
    ) -> dict[str, Any]:
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

        return await self.request('search/schedule-flights', payload)


@click.command()
@click.option('--origin', required=True, type=str, help='Origin code')
@click.option('--destination', default='', type=str, help='Destination code')
@click.option('--currency', required=True, type=str, help='Currency code')
@click.option('--travel_date', required=True, type=str, help='Date in YYYY-MM-DD format')
@click.option('--price', type=Decimal, help='Max price of the tickets')
@click.option('--limit', default=-1, type=int, help='Limit of records to fetch (default: all)')
def main(origin: str, destination: str, currency: str, travel_date: str, price: Decimal, limit: int):
    asyncio.run(run_main(origin, destination, currency, travel_date, price, limit))


async def run_main(origin: str, destination: str, currency: str, travel_date: str, price: Decimal, limit: int):
    fc = FlyoneClient()
    response = await fc.get_fare_stats(dep=origin, travel_date=travel_date, currency=currency)

    origin = response['origin']
    travel_date = response['travelDate']

    fares = [fare for fare in response['destinationFares'] if fare['price'] <= price]
    if limit >= 0:
        fares = fares[:limit]

    for n, fare in enumerate(sorted(fares, key=lambda f: f['price']), start=1):
        destination = fare['destination']
        airports_by_code = await fc.airport_by_code
        dep_airport = airports_by_code.get(origin) or Airport()
        arr_airport = airports_by_code.get(destination) or Airport()
        print(
            f'#{n} {travel_date} '
            f'{origin} <{dep_airport.name}> |{dep_airport.country}|'
            ' -> '
            f'{destination} <{arr_airport.name}> |{arr_airport.country}|: '
            f'{fare["price"]}'
        )

    print('\n', '-' * 42, '\n')

    if destination:
        response = await fc.get_flights(
            dep=origin, arr=destination, dep_date=travel_date, arr_date=travel_date, currency=currency
        )

        pprint(response)


if __name__ == '__main__':
    # TODO cloud function trigger that sends request to bot to inform users about cheap flights
    # TODO public API to build a web-site on top of it
    # TODO CLI and python library
    # TODO DB to analyse price changes and to store users subscriptions
    main()
