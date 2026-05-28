from decimal import Decimal

import aiohttp


class CurrencyConverter:
    BASE_URL = 'https://open.er-api.com/v6'

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session

    async def convert(self, amount: Decimal, from_cur: str, to_cur: str) -> Decimal:
        params = {'base': from_cur, 'symbols': to_cur}
        async with self._session.get(f'{self.BASE_URL}/latest/{from_cur}', params=params) as r:
            data = await r.json()
            print(data)
        return amount * Decimal(str(data['rates'][to_cur]))

    async def rates(self, base: str = 'EUR') -> dict[str, Decimal]:
        async with self._session.get(f'{self.BASE_URL}/latest/{base}') as r:
            data = await r.json()
        return {cur: Decimal(str(rate)) for cur, rate in data['rates'].items()}
