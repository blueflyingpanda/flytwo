from datetime import datetime
from urllib.parse import parse_qs, urlparse


class UrlParser:
    @staticmethod
    def parse(url: str) -> tuple[str, str, str]:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        src = query_params.get('depCity', [''])[0]
        dst = query_params.get('arrCity', [''])[0]
        travel_date = query_params.get('startDate', [''])[0]

        if travel_date:
            parsed_date = datetime.strptime(travel_date, '%d-%b-%Y')
            travel_date = parsed_date.strftime('%d.%m.%Y')

        return src, dst, travel_date
