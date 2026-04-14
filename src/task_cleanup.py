import asyncio

from dal import DataAccessLayer
from db import Direction


async def main():
    # Flight records are kept to track patterns using historical data.
    # await DataAccessLayer.cleanup_outdated(Flight)
    await DataAccessLayer.cleanup_outdated(Direction)


if __name__ == '__main__':
    asyncio.run(main())
