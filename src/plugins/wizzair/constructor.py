from url_constructor import BaseUrlConstructor


class WizzairUrlConstructor(BaseUrlConstructor):
    url_prefix = 'https://www.wizzair.com/en-gb/booking/select-flight'

    def construct(self) -> str:
        return f'{self.url_prefix}/{self.src.upper()}/{self.dst.upper()}/{self.travel_date:%Y-%m-%d}/null/1/0/0/null'
