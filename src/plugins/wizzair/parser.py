from datetime import datetime
from urllib.parse import urlparse

from parser import BaseUrlParser, ParsedUrl


class WizzairUrlParser(BaseUrlParser):
    @classmethod
    def can_parse(cls, url: str) -> bool:
        return url.startswith('https://www.wizzair.com/')

    def parse(self) -> ParsedUrl:
        parts = urlparse(self.url).path.strip('/').split('/')
        # path: {lang}/booking/select-flight/{src}/{dst}/{dep_date}/...
        try:
            src = parts[3]
            dst = parts[4]
            travel_date = datetime.strptime(parts[5], '%Y-%m-%d').strftime('%d.%m.%Y')
        except (IndexError, ValueError):
            src = dst = travel_date = ''

        return ParsedUrl(src, dst, travel_date)
