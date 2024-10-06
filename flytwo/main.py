import asyncio
from pprint import pprint

from client import FlyoneClient


async def main():
    fc = FlyoneClient()

    response = await fc.get_flights(
        dep='RMO', arr='EVN', dep_date='2024-10-30', arr_date='2024-10-30', currency='EUR'
    )
    pprint(response)

if __name__ == '__main__':
    asyncio.run(main())
