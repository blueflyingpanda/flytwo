from datetime import datetime, date

import pytest
from datetime import timedelta

from db import Flight
from dal import DataAccessLayer


@pytest.fixture
async def seed_flights(session):
    """
    Fixture to insert some initial test data into the database.
    """
    flight1 = Flight(
        id=1,
        src='LAX',
        dst='JFK',
        travel_date=date.today(),
        price=300,
        history=[
            {'price': 200, 'dt': datetime(2023, 10, 1).isoformat()},
            {'price': 250, 'dt': datetime(2023, 10, 15).isoformat()},
            {'price': 300, 'dt': datetime(2023, 10, 16).isoformat()},
        ]
    )
    flight2 = Flight(
        id=2,
        src='SFO',
        dst='SEA',
        travel_date=date.today(),
        price=150,
        history=[
            {'price': 150, 'dt': datetime(2023, 11, 15).isoformat()},
        ]
    )
    flight3 = Flight(
        id=3,
        src='ORD',
        dst='ATL',
        travel_date=date.today(),
        price=500,
        history=[
            {'price': 450, 'dt': datetime(2023, 9, 20).isoformat()},
            {'price': 500, 'dt': datetime(2023, 9, 29).isoformat()},
        ]
    )

    session.add_all([flight1, flight2, flight3])
    await session.commit()

@pytest.fixture
async def seed_flights_same_direction(session):
    flight1 = Flight(
        id=1,
        src='LAX',
        dst='JFK',
        travel_date=date.today() - timedelta(days=1),
        price=300,
        history=[
            {'price': 200, 'dt': datetime(2023, 10, 16).isoformat()},
        ]
    )
    flight2 = Flight(
        id=2,
        src='LAX',
        dst='JFK',
        travel_date=date.today(),
        price=150,
        history=[
            {'price': 100, 'dt': datetime(2023, 11, 15).isoformat()},
        ]
    )

    session.add_all([flight1, flight2])
    await session.commit()

@pytest.fixture
async def seed_flights_no_price(session):
    flight4 = Flight(
        id=4,
        src='NYC',
        dst='DCA',
        travel_date=date.today(),
        price=0,
        history=[
            {'price': 100, 'dt': datetime(2023, 11, 15).isoformat()}
        ]
    )
    flight5 = Flight(
        id=5,
        src='IAD',
        dst='BWI',
        travel_date=date.today(),
        price=0,
        history=[]
    )

    session.add_all([flight4, flight5])
    await session.commit()

@pytest.mark.asyncio
async def test_update_flights(session, seed_flights):
    """
    Test the `update_flights` method to ensure it updates prices and appends
    proper historical records to the history field.
    """

    updates = [
        {'id': 1, 'price': 350},
        {'id': 2, 'price': 180},
    ]

    await DataAccessLayer.update_flights(updates)

    flight1 = await session.get(Flight, 1)
    flight2 = await session.get(Flight, 2)
    flight3 = await session.get(Flight, 3)

    assert flight1.price == 350
    assert flight2.price == 180
    assert flight3.price == 500

    assert len(flight1.history) == 4
    assert flight1.history[-2]['price'] == 300
    assert flight1.history[-1]['price'] == 350
    assert isinstance(datetime.fromisoformat(flight1.history[-1]['dt']), datetime)

    assert len(flight2.history) == 2
    assert flight2.history[-2]['price'] == 150
    assert flight2.history[-1]['price'] == 180
    assert isinstance(datetime.fromisoformat(flight2.history[-1]['dt']), datetime)

    # remains unchanged
    assert len(flight3.history) == 2
    assert flight3.history[-1]['price'] == 500
    assert flight3.history[-1]['dt'] == datetime(2023, 9, 29).isoformat()


@pytest.mark.asyncio
async def test_get_direction_price_history(session, seed_flights, seed_flights_no_price):
    """
    Test if `get_direction_price_history` correctly retrieves flight price history.
    """
    today = date.today()
    result = await DataAccessLayer.get_direction_price_history('LAX', 'JFK')

    history = result[today]

    assert len(history) == 4  # 3 history + 1 current
    assert history[-2].price == 300  # previous price from history
    assert history[-1].price == 300  # current price

    result = await DataAccessLayer.get_direction_price_history('NYC', 'DCA')

    history = result[today]

    assert len(history) == 1  # No new entry since the price is 0. Free tickets don't exist
    assert history[-1].price == 100

    result = await DataAccessLayer.get_direction_price_history('IAD', 'BWI')
    assert today not in result # Empty history and price 0, nothing to show on graph


@pytest.mark.asyncio
async def test_get_direction_price_history_with_date(session, seed_flights_same_direction):
    """
    Test if `get_direction_price_history` correctly retrieves flight price history for a specific date.
    """
    today = date.today()
    result = await DataAccessLayer.get_direction_price_history('LAX', 'JFK', today)

    assert len(result) == 1

    history = result[today]

    assert len(history) == 2  # 1 history + 1 current
    assert history[-2].price == 100  # previous price from history
    assert history[-1].price == 150  # current price
