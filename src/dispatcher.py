import asyncio
import logging

import plugins  # noqa: F401 - triggers plugin registration via plugins/__init__.py
from airline import Airline
from client import Airport, BaseClient
from parser import BaseUrlParser


class AirlineDispatcher:
    def __init__(self, airline_names: set[str] | None = None):
        airlines = [airline for airline in Airline.__subclasses__() if airline.active]

        if airline_names:
            airlines = [airline for airline in airlines if airline.name in airline_names]

        self.parsers_by_airlines = {airline.name: airline.url_parser_cls for airline in airlines}
        self.clients_by_airlines = {airline.name: airline.client_cls for airline in airlines}

    def pick_parser(self, url: str) -> BaseUrlParser | None:
        for parser_cls in self.parsers_by_airlines.values():
            if parser_cls.can_parse(url):
                return parser_cls(url)
        return None

    def get_client_classes(self) -> list[type[BaseClient]]:
        return list(self.clients_by_airlines.values())

    async def get_airport_by_code(self) -> dict[str, Airport]:
        client_classes = self.get_client_classes()
        tasks = [client_cls().airport_by_code() for client_cls in client_classes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        airport_by_code: dict[str, Airport] = {}

        for client_cls, result in zip(client_classes, results, strict=True):
            if isinstance(result, Exception):
                logging.error('%s failed with error: %s', client_cls.__name__, result)
                continue
            airport_by_code |= result

        return airport_by_code


dispatcher = AirlineDispatcher()
