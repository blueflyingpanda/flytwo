import plugins  # noqa: F401 - triggers plugin registration via plugins/__init__.py
from airline import Airline
from client import BaseClient
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


dispatcher = AirlineDispatcher()
