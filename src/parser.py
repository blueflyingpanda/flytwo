import re
from abc import ABC, abstractmethod
from typing import NamedTuple

_TIME_PAT = r'(\d{1,2})(am|pm)'


class ParsedUrl(NamedTuple):
    src: str
    dst: str
    travel_date: str


class BaseUrlParser(ABC):
    def __init__(self, url: str):
        self.url = url

    @classmethod
    @abstractmethod
    def can_parse(cls, url: str) -> bool:
        """Return True if this parser can handle the given URL."""

    @abstractmethod
    def parse(self) -> ParsedUrl:
        """Extract src, dst, and travel_date from the URL."""


class ScheduleParser:
    @staticmethod
    def _to_24h(h: int, period: str) -> int:
        if period == 'am':
            return 0 if h == 12 else h
        return 12 if h == 12 else h + 12

    @classmethod
    def parse(cls, text: str) -> str | None:
        """Translate user-friendly schedule input to a rrule string, or None if invalid."""
        text = text.strip().lower()

        # Nh — every N hours
        m = re.fullmatch(r'(\d+)h', text)
        if m:
            n = int(m.group(1))
            return f'FREQ=HOURLY;INTERVAL={n}' if n >= 1 else None

        # 6pm — daily at a specific hour
        m = re.fullmatch(_TIME_PAT, text)
        if m:
            h = cls._to_24h(int(m.group(1)), m.group(2))
            return f'FREQ=DAILY;BYHOUR={h};BYMINUTE=0;BYSECOND=0'

        # 8am-11pm [Nh] — every N hours within a time range
        m = re.fullmatch(rf'{_TIME_PAT}-{_TIME_PAT}(?:\s+(\d+)h)?', text)
        if m:
            start = cls._to_24h(int(m.group(1)), m.group(2))
            end = cls._to_24h(int(m.group(3)), m.group(4))
            interval = int(m.group(5)) if m.group(5) else 1
            if start >= end or interval < 1:
                return None
            hours = ','.join(str(h) for h in range(start, end + 1, interval))
            return f'FREQ=DAILY;BYHOUR={hours};BYMINUTE=0;BYSECOND=0'

        return None
