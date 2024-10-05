import asyncio
from decimal import Decimal
from pprint import pprint
import click

from client import FlyoneClient, Airport


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
