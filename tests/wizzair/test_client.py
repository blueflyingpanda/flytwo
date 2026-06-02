from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from client import Airport, DestinationFare, FareStats, Flight
from plugins.wizzair.client import WizzairClient

AIRPORTS_RESPONSE = {
    'cities': [
        {'iata': 'RMO', 'shortName': 'Chisinau', 'countryName': 'Moldova', 'currencyCode': 'EUR'},
        {'iata': 'VRN', 'shortName': 'Verona', 'countryName': 'Italy', 'currencyCode': 'EUR'},
    ]
}

FARECHART_RESPONSE = {
    'outboundFlights': [
        {'date': '2026-06-03T00:00:00', 'price': {'amount': 49.99, 'currencyCode': 'EUR'}},
        {'date': '2026-06-04T00:00:00', 'price': {'amount': 0, 'currencyCode': 'EUR'}},  # should be skipped
    ],
    'returnFlights': [
        {'date': '2026-06-10T00:00:00', 'price': {'amount': 59.99, 'currencyCode': 'EUR'}},
    ],
}

SMART_SEARCH_RESPONSE = {
    'items': [
        {'outboundFlight': {'arrivalStation': 'VRN', 'regularPrice': {'amount': 39.99, 'currencyCode': 'EUR'}}},
        {
            'outboundFlight': {'arrivalStation': 'BCN', 'regularPrice': {'amount': 0, 'currencyCode': 'EUR'}}
        },  # should be skipped
    ]
}


def make_response(json_data: dict, status: int = 200):
    response = AsyncMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data)
    response.cookies = {}
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)
    return response


def make_session(response):
    session = MagicMock()
    session.get = MagicMock(return_value=response)
    session.post = MagicMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture
def client():
    c = WizzairClient()
    c._token = 'test-token'
    c._session_id = 'test-session'
    c._version = '28.10.0'
    return c


@pytest.fixture
def client_with_airports(client):
    client._airports_by_code = {
        'RMO': Airport(code='RMO', name='Chisinau', country='Moldova', currency='EUR'),
        'VRN': Airport(code='VRN', name='Verona', country='Italy', currency='EUR'),
    }
    return client


class TestAirportByCode:
    async def test_fetches_and_maps_airports(self, client):
        # Arrange
        response = make_response(AIRPORTS_RESPONSE)
        session = make_session(response)

        # Act
        with patch('aiohttp.ClientSession', return_value=session):
            result = await client.airport_by_code()

        # Assert
        assert result == {
            'RMO': Airport(code='RMO', name='Chisinau', country='Moldova', currency='EUR'),
            'VRN': Airport(code='VRN', name='Verona', country='Italy', currency='EUR'),
        }

    async def test_returns_cached_result_without_request(self, client_with_airports):
        # Arrange
        expected = client_with_airports._airports_by_code

        # Act
        with patch('aiohttp.ClientSession') as mock_session:
            result = await client_with_airports.airport_by_code()

        # Assert
        assert result == expected
        mock_session.assert_not_called()


class TestGetFlights:
    async def test_returns_parsed_outbound_and_inbound_flights(self, client_with_airports):
        # Arrange
        response = make_response(FARECHART_RESPONSE)
        session = make_session(response)

        # Act
        with patch('aiohttp.ClientSession', return_value=session):
            outbound, inbound = await client_with_airports.get_flights(
                dep='RMO',
                arr='VRN',
                dep_date='2026-06-03',
                arr_date='2026-06-10',
                currency='EUR',
            )

        # Assert
        assert len(outbound) == 1
        assert outbound[0] == Flight(
            from_airport=Airport(code='RMO', name='Chisinau', country='Moldova', currency='EUR'),
            to_airport=Airport(code='VRN', name='Verona', country='Italy', currency='EUR'),
            travel_date=date(day=3, month=6, year=2026),
            currency='EUR',
            price=Decimal('49.99'),
            airline='wizzair',
        )

        assert len(inbound) == 1
        assert inbound[0] == Flight(
            from_airport=Airport(code='VRN', name='Verona', country='Italy', currency='EUR'),
            to_airport=Airport(code='RMO', name='Chisinau', country='Moldova', currency='EUR'),
            travel_date=date(day=10, month=6, year=2026),
            currency='EUR',
            price=Decimal('59.99'),
            airline='wizzair',
        )

    async def test_skips_flights_with_zero_price(self, client_with_airports):
        # Arrange
        response = make_response(FARECHART_RESPONSE)
        session = make_session(response)

        # Act
        with patch('aiohttp.ClientSession', return_value=session):
            outbound, _ = await client_with_airports.get_flights(
                dep='RMO',
                arr='VRN',
                dep_date='2026-06-03',
                arr_date='2026-06-10',
                currency='EUR',
            )

        # Assert — raw response has 2 outbound entries but one has amount=0
        assert len(outbound) == 1

    async def test_sends_both_legs_in_payload(self, client_with_airports):
        # Arrange
        response = make_response({'outboundFlights': [], 'returnFlights': []})
        session = make_session(response)

        # Act
        with patch('aiohttp.ClientSession', return_value=session):
            await client_with_airports.get_flights(
                dep='RMO',
                arr='VRN',
                dep_date='2026-06-03',
                arr_date='2026-06-10',
                currency='EUR',
                before=5,
            )

        # Assert
        _, kwargs = session.post.call_args
        payload = kwargs['json']
        assert payload['dayInterval'] == 5
        assert payload['flightList'] == [
            {'departureStation': 'RMO', 'arrivalStation': 'VRN', 'date': '2026-06-03'},
            {'departureStation': 'VRN', 'arrivalStation': 'RMO', 'date': '2026-06-10'},
        ]


class TestGetFareStats:
    async def test_returns_fare_stats_with_destination_fares(self, client):
        # Arrange
        response = make_response(SMART_SEARCH_RESPONSE)
        session = make_session(response)

        # Act
        with patch('aiohttp.ClientSession', return_value=session):
            result = await client.get_fare_stats(dep='RMO', travel_date='2026-05-28', currency='EUR')

        # Assert
        assert result == FareStats(
            origin='RMO',
            travelDate='2026-05-28',
            destinationFares=[
                DestinationFare(destination='VRN', price=Decimal('39.99'), currency='EUR', airline='wizzair')
            ],
        )

    async def test_skips_destinations_with_zero_price(self, client):
        # Arrange
        response = make_response(SMART_SEARCH_RESPONSE)
        session = make_session(response)

        # Act
        with patch('aiohttp.ClientSession', return_value=session):
            result = await client.get_fare_stats(dep='RMO', travel_date='2026-05-28', currency='EUR')

        # Assert — raw response has 2 destinations but BCN has amount=0
        assert len(result.destinationFares) == 1

    async def test_sends_correct_payload(self, client):
        # Arrange
        response = make_response({'outboundFlights': []})
        session = make_session(response)

        # Act
        with patch('aiohttp.ClientSession', return_value=session):
            await client.get_fare_stats(dep='RMO', travel_date='2026-05-28', currency='EUR')

        # Assert
        _, kwargs = session.post.call_args
        payload = kwargs['json']
        assert payload['departureStations'] == ['RMO']
        assert payload['departureDate'] == '2026-05-28'
        assert payload['isReturnFlight'] is False
