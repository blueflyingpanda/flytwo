import asyncio

from dal import DataAccessLayer
from db import Direction, Flight


async def main():
    await DataAccessLayer.cleanup_outdated(Flight)
    await DataAccessLayer.cleanup_outdated(Direction)


if __name__ == '__main__':
    asyncio.run(main())
