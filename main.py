import aiohttp
import asyncio
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from functools import cached_property
from pprint import pprint
from typing import Any

import click
import requests


@dataclass
class Airport:
    code: str = ''
    name: str = ''
    country: str = ''


class FlyoneClient:

    view_url = 'https://bookings.flyone.eu/FareView'
    api_url = 'https://api2.flyone.eu/api'

    default_currency = 'EUR'

    def __init__(self):
        self._token: str = ''

    def refresh_token(self):
        response = requests.get(self.view_url)
        self._token = response.cookies.get('COOKIE_TOKEN')

    @property
    def token(self):
        if not self._token:
            self.refresh_token()

        return self._token

    def request(self, path: str, data: dict | list, retry: bool = False) -> dict:
        """ TODO error handling for 200 and
                {
                    "token": null,
                    "flightSchedule": null,
                    "result": {
                        "isSuccess": false,
                        "msgs": [
                            {
                                "code": 1009,
                                "msgText": "Departure Date must be Today or Future Date",
                                "paxKey": null
                            }
                        ]
                    }
                }
        """
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.post(f'{self.api_url}/{path}', json=data, headers=headers)

        if response.status_code != 200:

            if response.status_code == 401 and not retry:
                self.refresh_token()
                self.request(path, data, retry=True)
            else:
                raise Exception(f'{response.status_code}: {response.text}')

        return response.json(parse_float=Decimal)

    @cached_property
    def airport_by_code(self) -> dict[str, Airport]:
        result: dict[str, Airport] = {}
        response = self.request('Routes/get-routes', {})

        for route in response['routes']:
            code = route['depCode']
            result[code] = Airport(code, route['depAirportName'], route['countryName'])

        return result

    def get_fare_stats(self, *, dep: str, travel_date: str = '', currency: str = '') -> dict[str, Any]:
        payload = {
            'origin': dep,
            'travelDate': travel_date or datetime.now().strftime('%Y-%m-%d'),
            'currencyCode': currency or self.default_currency,
        }

        return self.request('search/get-route-fare', payload)

    def get_flights(
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

        return self.request('search/schedule-flights', payload)


@click.command()
@click.option('--origin', required=True, type=str, help='Origin code')
@click.option('--destination', default='', type=str, help='Destination code')
@click.option('--currency', required=True, type=str, help='Currency code')
@click.option('--travel_date', required=True, type=str, help='Date in YYYY-MM-DD format')
@click.option('--price', type=Decimal, help='Max price of the tickets')
@click.option('--limit', default=-1, type=int, help='Limit of records to fetch (default: all)')
def main(origin: str, destination: str, currency: str, travel_date: str, price: Decimal, limit: int):

    fc = FlyoneClient()
    response = fc.get_fare_stats(dep=origin, travel_date=travel_date, currency=currency)

    origin = response['origin']
    travel_date = response['travelDate']

    fares = [fare for fare in response['destinationFares'] if fare['price'] <= price]
    if limit >= 0:
        fares = fares[:limit]

    for n, fare in enumerate(sorted(fares, key=lambda f: f['price']), start=1):
        destination = fare['destination']
        dep_airport = fc.airport_by_code.get(origin) or Airport()
        arr_airport = fc.airport_by_code.get(destination) or Airport()
        print(
            f'#{n} {travel_date} '
            f'{origin} <{dep_airport.name}> |{dep_airport.country}|'
            ' -> '
            f'{destination} <{arr_airport.name}> |{arr_airport.country}|: '
            f'{fare["price"]}'
        )

    print('\n', '-' * 42, '\n')

    if destination:
        response = fc.get_flights(
            dep=origin, arr=destination, dep_date=travel_date, arr_date=travel_date, currency=currency
        )

        pprint(response)


if __name__ == '__main__':
    # TODO cloud function trigger that sends request to bot to inform users about cheap flights
    # TODO public API to build a web-site on top of it
    # TODO CLI and python library
    # TODO DB to analyse price changes and to store users subscriptions
    # TODO make async
    main()
