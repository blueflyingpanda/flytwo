from datetime import datetime
from decimal import Decimal
from typing import Any

import aiohttp

from bot.notifier import TgBotNotifier
from client import Airport, BaseClient, ClientError, DestinationFare, FareStats, Flight
from dal import DataAccessLayer


class WizzairErrorNotifier:
    def __init__(self, maintainer_tg_id: int):
        self.tg_notifier = TgBotNotifier(maintainer_tg_id)

    async def notify_on_version_mismatch(self, version: str):
        await self.tg_notifier.send_err(
            f'404: Wizzair API version mismatch: version {version} is no longer available. '
            'Go to https://www.wizzair.com/en-gb and look for https://be.wizzair.com/{{VERSION}}/Api requests. '
            'Update WIZZAIR_API_VERSION settings accordingly.'
        )


class WizzairClient(BaseClient):
    """api_url and auth_url are dynamic for Wizzair, so we implement them as methods instead of class attributes."""

    def __init__(self):
        super().__init__()
        self._session_id: str = ''
        self._version: str = ''

    async def api_url(self) -> str:
        return f'https://be.wizzair.com/{await self._get_version()}/Api'

    async def auth_url(self) -> str:
        return f'{await self.api_url()}/asset/culture'

    async def _get_session(self) -> str:
        if not self._session_id:
            await self._refresh_token()
        return self._session_id

    async def _get_version(self) -> str:
        if not self._version:
            await self._refresh_version()
        return self._version

    async def _refresh_version(self):
        self._version = await DataAccessLayer.get_setting('WIZZAIR_API_VERSION')

    async def _refresh_token(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                await self.auth_url(),
                json={'languageCode': 'en-gb'},
                headers={'accept': 'application/json', 'content-type': 'application/json'},
            ) as response:
                if response.status != 200:
                    if response.status == 404:
                        maintainer_tg_id = await DataAccessLayer.get_setting('MAINTAINER_TG_ID')
                        err_notifier = WizzairErrorNotifier(int(maintainer_tg_id))
                        await err_notifier.notify_on_version_mismatch(await self._get_version())

                    raise ClientError(f'Wizzair auth failed: {response.status}: {await response.text()}')
                self._session_id = response.cookies['ASP.NET_SessionId'].value
                self._token = response.cookies['RequestVerificationToken'].value

    async def _request(self, path: str, data: dict | list, is_retry: bool = False) -> dict[str, Any]:
        session_id = await self._get_session()
        csrf_token = await self._get_token()

        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'x-requestverificationtoken': csrf_token,
            'cookie': f'ASP.NET_SessionId={session_id}; RequestVerificationToken={csrf_token}',
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f'{await self.api_url()}/{path}', json=data, headers=headers) as response:
                if response.status in (401, 403) and not is_retry:
                    self._token = ''
                    self._session_id = ''
                    await self._refresh_token()
                    return await self._request(path, data, is_retry=True)

                if response.status != 200:
                    raise ClientError(f'{response.status}: {await response.text()}')

                return await response.json()

    async def airport_by_code(self) -> dict[str, Airport]:
        if self._airports_by_code:
            return self._airports_by_code

        csrf_token = await self._get_token()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{await self.api_url()}/asset/map',
                params={'languageCode': 'en-gb', 'withConnections': 'true'},
                headers={'accept': 'application/json', 'x-requestverificationtoken': csrf_token},
            ) as response:
                if response.status != 200:
                    raise ClientError(f'Wizzair airports failed: {response.status}')
                data = await response.json()

        self._airports_by_code = {
            city['iata']: Airport(
                code=city['iata'],
                name=city['shortName'].strip(),
                country=city['countryName'],
                currency=city['currencyCode'],
            )
            for city in data.get('cities', [])
        }
        return self._airports_by_code

    async def get_flights(
        self,
        *,
        dep: str,
        arr: str,
        dep_date: str,
        arr_date: str,
        currency: str,
        before: int = 10,
        after: int = 10,
        passengers: int = 1,
    ) -> tuple[list[Flight], list[Flight]]:
        """currency and after parameters are not supported by Wizzair API, but we keep them for compatibility with the interface defined in BaseClient."""
        payload = {
            'isRescueFare': False,
            'adultCount': passengers,
            'childCount': 0,
            'dayInterval': before,
            'wdc': False,
            'isFlightChange': False,
            'flightList': [
                {'departureStation': dep, 'arrivalStation': arr, 'date': dep_date},
                {'departureStation': arr, 'arrivalStation': dep, 'date': arr_date},
            ],
        }

        result = await self._request('asset/farechart', payload)

        airport_by_code = await self.airport_by_code()

        if dep not in airport_by_code or arr not in airport_by_code:
            return [], []

        dep_airport = airport_by_code[dep]
        arr_airport = airport_by_code[arr]

        def parse_flights(raw_flights: list[dict], from_airport: Airport, to_airport: Airport) -> list[Flight]:
            flights = []
            for flight in raw_flights:
                price_data = flight.get('price', {})
                currency_code = price_data.get('currencyCode', '')
                amount = price_data.get('amount')
                if not amount:
                    continue
                travel_date = datetime.fromisoformat(flight['date']).date()
                flights.append(
                    Flight(
                        from_airport=from_airport,
                        to_airport=to_airport,
                        travel_date=travel_date,
                        currency=currency_code,
                        price=Decimal(str(amount)),
                        airline='wizzair',
                    )
                )
            return flights

        outbound = parse_flights(result.get('outboundFlights', []), dep_airport, arr_airport)
        inbound = parse_flights(result.get('returnFlights', []), arr_airport, dep_airport)

        return outbound, inbound

    async def get_fare_stats(self, *, dep: str, travel_date: str, currency: str) -> FareStats:
        payload = {
            'departureStations': [dep],
            'arrivalStations': None,
            'stdPlan': None,
            'isReturnFlight': False,
            'tripDuration': 'anytime',
            'pax': 1,
            'dateFilterType': 'Exact',
            'departureDate': travel_date,
            'returnDate': None,
        }
        result = await self._request('search/SmartSearchCheapFlightsV2', payload)

        destination_fares = []
        for flight in result.get('items', []):
            outbound = flight.get('outboundFlight', {})
            price = outbound.get('regularPrice', {})
            if not price.get('amount'):
                continue
            destination_fares.append(
                DestinationFare(
                    destination=outbound.get('arrivalStation', ''),
                    price=Decimal(str(price.get('amount'))),
                    currency=price.get('currencyCode', ''),
                    airline='wizzair',
                )
            )

        return FareStats(origin=dep, travelDate=travel_date, destinationFares=destination_fares)
