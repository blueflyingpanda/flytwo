from client import BaseClient
from parser import BaseUrlParser
from url_constructor import BaseUrlConstructor


class Airline:
    name: str = ''
    active: bool = True
    url_parser_cls = BaseUrlParser
    url_constructor_cls = BaseUrlConstructor
    client_cls = BaseClient
