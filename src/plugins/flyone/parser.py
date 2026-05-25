from datetime import datetime
from urllib.parse import parse_qs, urlparse

from parser import BaseUrlParser, ParsedUrl


class FlyoneUrlParser(BaseUrlParser):
    @classmethod
    def can_parse(cls, url: str) -> bool:
        return url.startswith('https://bookings.flyone.eu/FlightResult')

    def parse(self) -> ParsedUrl:
        parsed_url = urlparse(self.url)
        query_params = parse_qs(parsed_url.query)

        src = query_params.get('depCity', [''])[0]
        dst = query_params.get('arrCity', [''])[0]
        travel_date = query_params.get('startDate', [''])[0]

        if travel_date:
            parsed_date = datetime.strptime(travel_date, '%d-%b-%Y')
            travel_date = parsed_date.strftime('%d.%m.%Y')

        return ParsedUrl(src, dst, travel_date)
