from airline import Airline
from plugins.wizzair.client import WizzairClient
from plugins.wizzair.constructor import WizzairUrlConstructor
from plugins.wizzair.parser import WizzairUrlParser


class Wizzair(Airline):
    name = 'wizzair'
    url_parser_cls = WizzairUrlParser
    url_constructor_cls = WizzairUrlConstructor
    client_cls = WizzairClient
