from decimal import Decimal

from bot.notifier import TgBotNotifier
from client.client import Airport, Flight


async def test_price_change():
    tg_notifier = TgBotNotifier(chat_id=0)

    new_flight = Flight(
        from_airport=Airport(code='RMO'),
        to_airport=Airport(code='EVN'),
        travel_date='29.1.2024',
        currency='EUR',
        price=Decimal(80),
    )

    increased_flight = Flight(
        from_airport=Airport(code='RMO'),
        to_airport=Airport(code='EVN'),
        travel_date='30.1.2024',
        currency='EUR',
        price=Decimal(100),
        prev_price=Decimal(75),
    )

    decreased_flight = Flight(
        from_airport=Airport(code='RMO'),
        to_airport=Airport(code='EVN'),
        travel_date='31.1.2024',
        currency='EUR',
        price=Decimal(50),
        prev_price=Decimal(110),
    )

    msg = await tg_notifier.form_msg([new_flight, increased_flight, decreased_flight])

    new, increased, decreased = msg.split('\n')

    assert new == '29.01.2024:  80€   '
    assert increased == '30.01.2024: 100€ ❌ ⬆️ 25€ (was  75€)'
    assert decreased == '31.01.2024:  50€ ✅ ⬇️ 60€ (was 110€)'


async def test_form_err_msg():
    msg1 = await TgBotNotifier.form_err('Error: something went wrong')
    msg2 = await TgBotNotifier.form_err('something went wrong')

    assert msg1 == msg2
