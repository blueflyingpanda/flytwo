from abc import ABC, abstractmethod
from datetime import date


class BaseUrlConstructor(ABC):
    url_prefix: str = ''

    def __init__(self, src: str, dst: str, travel_date: date):
        self.src = src
        self.dst = dst
        self.travel_date = travel_date

    @abstractmethod
    def construct(self) -> str:
        """Construct airline URL from flight details."""
