from url_constructor import BaseUrlConstructor


class FlyoneUrlConstructor(BaseUrlConstructor):
    url_prefix = 'https://bookings.flyone.eu/FlightResult'

    def construct(self) -> str:
        return f'{self.url_prefix}?depCity={self.src.upper()}&arrCity={self.dst.upper()}&adult=1&startDate={self.travel_date:%d-%b-%Y}'
