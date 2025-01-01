import asyncio

from dal import DataAccessLayer
from db import Flight, Direction


async def main(event: dict | None = None, context=None):
    await DataAccessLayer.cleanup_outdated(Flight)
    await DataAccessLayer.cleanup_outdated(Direction)


if __name__ == '__main__':
    asyncio.run(main())