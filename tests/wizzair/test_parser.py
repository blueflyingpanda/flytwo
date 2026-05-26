from plugins.wizzair.parser import WizzairUrlParser

BASE_URL = 'https://www.wizzair.com/en-gb/booking/select-flight/RMO/CPH/2026-08-07/2026-08-31/1/0/0/null'


def test_wizzair_url_parser():
    # Arrange
    url = BASE_URL

    # Act
    src, dst, travel_date = WizzairUrlParser(url).parse()

    # Assert
    assert src == 'RMO'
    assert dst == 'CPH'
    assert travel_date == '07.08.2026'


def test_wizzair_url_parser_too_short():
    # Arrange — URL that matches can_parse but has no flight path segments
    url = 'https://www.wizzair.com/en-gb/booking/select-flight'

    # Act
    src, dst, travel_date = WizzairUrlParser(url).parse()

    # Assert
    assert src == ''
    assert dst == ''
    assert travel_date == ''


def test_wizzair_url_parser_invalid_date():
    # Arrange
    url = BASE_URL.replace('/2026-08-07/', '/not-a-date/')

    # Act
    src, dst, travel_date = WizzairUrlParser(url).parse()

    # Assert
    assert src == ''
    assert dst == ''
    assert travel_date == ''


def test_wizzair_can_parse():
    assert WizzairUrlParser.can_parse(BASE_URL) is True
    assert WizzairUrlParser.can_parse('https://bookings.flyone.eu/FlightResult') is False
