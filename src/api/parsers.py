from api.common import bad_request
from parser import ScheduleParser
from price import Price


def parse_price(value: int | str) -> int:
    try:
        return int(Price(value))
    except ValueError as e:
        raise bad_request(str(e))


def parse_schedule(pattern: str) -> str:
    rrule = ScheduleParser.parse(pattern)
    if rrule is None:
        raise bad_request('Invalid schedule. Examples: 1h, 4h, 6pm, 8am-11pm, 8am-11pm 2h.')
    return rrule
