from airline import Airline
from plugins.wizzair.client import WizzairClient
from plugins.wizzair.parser import WizzairUrlParser


class Wizzair(Airline):
    name = 'wizzair'
    url_parser_cls = WizzairUrlParser
    client_cls = WizzairClient
