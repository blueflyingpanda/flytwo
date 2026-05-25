from client import BaseClient
from parser import BaseUrlParser


class Airline:
    name: str = ''
    active: bool = True
    url_parser_cls = BaseUrlParser
    client_cls = BaseClient
