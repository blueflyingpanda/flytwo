from airline import Airline
from plugins.flyone.client import FlyoneClient
from plugins.flyone.parser import FlyoneUrlParser


class Flyone(Airline):
    name = 'flyone'
    url_parser_cls = FlyoneUrlParser
    client_cls = FlyoneClient
