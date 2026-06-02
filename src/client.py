from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, TypeAdapter


class Direction(Enum):
    FORWARD = 1
    BACKWARD = 2


class Airport(BaseModel):
    code: str = ''
    name: str = ''
    country: str = ''
    currency: str = ''


class Flight(BaseModel):
    from_airport: Airport
    to_airport: Airport
    travel_date: date
    currency: str
    price: Decimal
    airline: str
    prev_price: Decimal | None = None

    def __hash__(self) -> int:
        return hash(f'{self.airline}{self.from_airport.code}{self.to_airport.code}{self.travel_date:%d.%m.%Y}')

    def __eq__(self, other) -> bool:
        import db  # import is placed here deliberately to be able to use the client without db

        if isinstance(other, db.Flight):
            # to get right associated stored in db flight in FlightsChangeDetector
            return (
                self.airline == other.airline
                and self.from_airport.code == other.src
                and self.to_airport.code == other.dst
                and self.travel_date == other.travel_date
            )

        return super().__eq__(other)

    def __lt__(self, other) -> bool:
        return (self.travel_date, self.airline) < (other.travel_date, other.airline)


FLIGHTS_TYPE_ADAPTER = TypeAdapter(list[Flight])


class DestinationFare(BaseModel):
    destination: str
    price: Decimal
    currency: str = 'EUR'
    airline: str = 'flyone'


class FareStats(BaseModel):
    origin: str
    travelDate: str
    destinationFares: list[DestinationFare]


class ClientError(Exception):
    """Custom exception for client errors."""


class MissingRouteError(ClientError):
    """Route was not found."""


class BaseClient(ABC):
    api_url: str
    auth_url: str

    def __init__(self):
        self._token: str = ''
        self._airports_by_code: dict[str, Airport] = {}

    async def _get_token(self) -> str:
        if not self._token:
            await self._refresh_token()
        return self._token

    @abstractmethod
    async def _refresh_token(self):
        """Refresh the authentication token."""

    @abstractmethod
    async def _request(self, path: str, data: dict | list) -> dict[str, Any]:
        """Make an authenticated request to the API."""

    @abstractmethod
    async def airport_by_code(self) -> dict[str, 'Airport']:
        """Fetch and return a mapping of airport codes to Airport objects."""

    @abstractmethod
    async def get_fare_stats(self, *, dep: str, travel_date: str, currency: str) -> 'FareStats':
        """Fetch fare statistics from the specified origin."""

    @abstractmethod
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
        """Fetch and return available forward and backward flights for the specified criteria."""
