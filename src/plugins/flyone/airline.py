from airline import Airline
from plugins.flyone.client import FlyoneClient
from plugins.flyone.constructor import FlyoneUrlConstructor
from plugins.flyone.parser import FlyoneUrlParser


class Flyone(Airline):
    name = 'flyone'
    url_parser_cls = FlyoneUrlParser
    url_constructor_cls = FlyoneUrlConstructor
    client_cls = FlyoneClient
