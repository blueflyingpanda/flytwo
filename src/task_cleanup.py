import asyncio

from dal import DataAccessLayer


async def main(event: dict | None = None, context=None):
    await DataAccessLayer.cleanup_outdated_flights()


if __name__ == '__main__':
    asyncio.run(main())