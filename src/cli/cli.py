import asyncio
import logging
from decimal import Decimal

import click

from client import Airport, FareStats, Flight
from dispatcher import dispatcher


class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    RESET = '\033[0m'


def display_flights(flights: list[Flight], price_limit: Decimal) -> None:
    flights = [flight for flight in flights if price_limit is None or flight.price <= price_limit]
    if not flights:
        return

    prices = [flight.price for flight in flights]
    min_price = min(prices)
    max_price = max(prices)

    for flight in flights:
        f_airport = flight.from_airport
        t_airport = flight.to_airport

        day, month, year = str(flight.travel_date.day), str(flight.travel_date.month), str(flight.travel_date.year)
        formatted_date = f'{day.zfill(2)}.{month}.{year}'

        from_airport_str = f'{f_airport.code} <{f_airport.name}> |{f_airport.country}|'
        to_airport_str = f'{t_airport.code} <{t_airport.name}> |{t_airport.country}|'
        price = f'{flight.price}'

        if flight.price == min_price:
            color = Color.GREEN
        elif flight.price == max_price:
            color = Color.RED
        else:
            color = Color.RESET

        click.echo(
            f'{color}{formatted_date}: {from_airport_str.ljust(44)} -> {to_airport_str.ljust(44)} '
            f'- {price.rjust(5)} {flight.currency} [{flight.airline}]{Color.RESET}'
        )


def display_fares(response: FareStats, airports_by_code: dict[str, Airport], limit: int, price: Decimal) -> None:
    origin = response.origin
    travel_date = response.travelDate

    fares = [fare for fare in response.destinationFares if price is None or fare.price <= price]
    fares = sorted(fares, key=lambda f: f.price)
    if limit >= 0:
        fares = fares[:limit]

    for n, fare in enumerate(fares, start=1):
        destination = fare.destination
        dep_airport = airports_by_code.get(origin) or Airport()
        arr_airport = airports_by_code.get(destination) or Airport()

        dep_airport_str = f'{dep_airport.code} <{dep_airport.name}> |{dep_airport.country}|'
        arr_airport_str = f'{arr_airport.code} <{arr_airport.name}> |{arr_airport.country}|'
        price_str = f'{fare.price}'

        click.echo(
            f'#{str(n).zfill(3)} {travel_date} '
            f'{dep_airport_str.ljust(44)} -> {arr_airport_str.ljust(44)} '
            f'- {price_str.rjust(5)} {fare.currency}'
        )


async def run_fares(origin: str, currency: str, travel_date: str, price: Decimal, limit: int):
    airport_by_code: dict[str, Airport] = await dispatcher.get_airport_by_code()

    async def process_client(client_cls):
        try:
            response = await client_cls().get_fare_stats(dep=origin, travel_date=travel_date, currency=currency)
            display_fares(response, airport_by_code, limit, price)
        except Exception:
            logging.exception('%s failed to fetch fare stats', client_cls.__name__)

    tasks = [process_client(cls) for cls in dispatcher.get_client_classes()]
    await asyncio.gather(*tasks)


async def run_flights(origin: str, destination: str, currency: str, travel_date: str, price: Decimal):
    async def process_client(client_cls):
        forward, backward = await client_cls().get_flights(
            dep=origin, arr=destination, dep_date=travel_date, arr_date=travel_date, currency=currency
        )

        click.echo('Forward Flights:\n')
        display_flights(forward, price)
        click.echo('\nBackward Flights:\n')
        display_flights(backward, price)

    tasks = [process_client(cls) for cls in dispatcher.get_client_classes()]
    await asyncio.gather(*tasks)


@click.command()
@click.option('--origin', required=True, type=str, help='Origin code')
@click.option('--currency', required=True, type=str, help='Currency code')
@click.option('--travel_date', required=True, type=str, help='Date in YYYY-MM-DD format')
@click.option('--price', type=Decimal, help='Max price of the tickets')
@click.option('--limit', default=-1, type=int, help='Limit of records to fetch (default: all)')
def fares(origin: str, currency: str, travel_date: str, price: Decimal, limit: int):
    """Fetch fares from specified origin."""
    asyncio.run(run_fares(origin, currency, travel_date, price, limit))


@click.command()
@click.option('--origin', required=True, type=str, help='Origin code')
@click.option('--destination', required=True, type=str, help='Destination code')
@click.option('--currency', required=True, type=str, help='Currency code')
@click.option('--travel_date', required=True, type=str, help='Date in YYYY-MM-DD format')
@click.option('--price', type=Decimal, help='Max price of the tickets')
def flights(origin: str, destination: str, currency: str, travel_date: str, price: Decimal):
    """Fetch flights to specified destinations."""
    asyncio.run(run_flights(origin, destination, currency, travel_date, price))


@click.group()
def cli():
    """A CLI tool with fares and flights commands."""


cli.add_command(fares)
cli.add_command(flights)

if __name__ == '__main__':
    cli()
