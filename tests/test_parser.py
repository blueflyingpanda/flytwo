from bot.parser import UrlParser


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
