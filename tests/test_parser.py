from datetime import datetime

from dateutil.rrule import rrulestr

from bot.parser import ScheduleParser, UrlParser


def test_url_parser():
    url = (
        'https://bookings.flyone.eu/FlightResult'
        '?depCityName=Кишинев+%28RMO%29'
        '&depCity=RMO'
        '&arrCityName=Прага+%28PRG%29'
        '&arrCity=PRG'
        '&adult=1'
        '&child=0'
        '&infant=0'
        '&startDate=02-Jan-2025'
        '&endDate=05-Jan-2025'
        '&radio=on'
        '&promocode='
        '&currency=EUR'
        '&sid=99'
    )

    # happy pass
    src, dst, travel_date = UrlParser.parse(url)
    assert src == 'RMO'
    assert dst == 'PRG'
    assert travel_date == '02.01.2025'

    # missing depCity
    url = url.replace('&depCity=RMO', '')

    src, dst, travel_date = UrlParser.parse(url)
    assert src == ''
    assert dst == 'PRG'
    assert travel_date == '02.01.2025'

    # missing arrCity
    url = url.replace('&arrCity=PRG', '')

    src, dst, travel_date = UrlParser.parse(url)
    assert src == ''
    assert dst == ''
    assert travel_date == '02.01.2025'

    # missing startDate
    url = url.replace('&startDate=02-Jan-2025', '')

    src, dst, travel_date = UrlParser.parse(url)
    assert src == ''
    assert dst == ''
    assert travel_date == ''


DTSTART = datetime(2024, 1, 1, 0, 0)


def is_valid_rrule(rrule_str: str) -> bool:
    try:
        rule = rrulestr(rrule_str, dtstart=DTSTART)
        return rule.after(DTSTART) is not None
    except Exception:
        return False


def test_schedule_parser_every_hour():
    # Arrange
    text = '1h'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result == 'FREQ=HOURLY;INTERVAL=1'
    assert is_valid_rrule(result)


def test_schedule_parser_every_n_hours():
    # Arrange
    text = '4h'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result == 'FREQ=HOURLY;INTERVAL=4'
    assert is_valid_rrule(result)


def test_schedule_parser_daily_at_hour_pm():
    # Arrange
    text = '6pm'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result == 'FREQ=DAILY;BYHOUR=18;BYMINUTE=0;BYSECOND=0'
    assert is_valid_rrule(result)


def test_schedule_parser_daily_at_hour_am():
    # Arrange
    text = '9am'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result == 'FREQ=DAILY;BYHOUR=9;BYMINUTE=0;BYSECOND=0'
    assert is_valid_rrule(result)


def test_schedule_parser_daily_midnight():
    # Arrange — 12am is midnight (hour 0)
    text = '12am'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result == 'FREQ=DAILY;BYHOUR=0;BYMINUTE=0;BYSECOND=0'
    assert is_valid_rrule(result)


def test_schedule_parser_daily_noon():
    # Arrange — 12pm is noon (hour 12)
    text = '12pm'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result == 'FREQ=DAILY;BYHOUR=12;BYMINUTE=0;BYSECOND=0'
    assert is_valid_rrule(result)


def test_schedule_parser_range_default_interval():
    # Arrange — every hour from 8am to 11pm inclusive
    text = '8am-11pm'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result == 'FREQ=DAILY;BYHOUR=8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23;BYMINUTE=0;BYSECOND=0'
    assert is_valid_rrule(result)


def test_schedule_parser_range_with_interval():
    # Arrange — every 2 hours from 8am to 11pm
    text = '8am-11pm 2h'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result == 'FREQ=DAILY;BYHOUR=8,10,12,14,16,18,20,22;BYMINUTE=0;BYSECOND=0'
    assert is_valid_rrule(result)


def test_schedule_parser_invalid_zero_interval():
    # Arrange
    text = '0h'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result is None


def test_schedule_parser_invalid_same_start_end():
    # Arrange — start equals end, no range
    text = '8am-8am'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result is None


def test_schedule_parser_invalid_reversed_range():
    # Arrange — end before start
    text = '11pm-8am'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result is None


def test_schedule_parser_invalid_garbage():
    # Arrange
    text = 'every wednesday'
    # Act
    result = ScheduleParser.parse(text)
    # Assert
    assert result is None
