from datetime import datetime

import pytest
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
        travel_date=datetime.today(),
        price=300,
        history=[
            {'price': 200, 'dt': datetime(2023, 10, 1).isoformat()},
            {'price': 250, 'dt': datetime(2023, 10, 15).isoformat()}
        ]
    )
    flight2 = Flight(
        id=2,
        src='SFO',
        dst='SEA',
        travel_date=datetime.today(),
        price=150,
        history=[]
    )
    flight3 = Flight(
        id=3,
        src='ORD',
        dst='ATL',
        travel_date=datetime.today(),
        price=500,
        history=[
            {'price': 450, 'dt': datetime(2023, 9, 20).isoformat()}
        ]
    )

    session.add_all([flight1, flight2, flight3])
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

    assert len(flight1.history) == 3
    assert flight1.history[-1]['price'] == 300
    assert isinstance(datetime.fromisoformat(flight1.history[-1]['dt']), datetime)

    assert len(flight2.history) == 1
    assert flight2.history[-1]['price'] == 150
    assert isinstance(datetime.fromisoformat(flight2.history[-1]['dt']), datetime)

    # remains unchanged
    assert len(flight3.history) == 1
    assert flight3.history[0]['price'] == 450
    assert flight3.history[0]['dt'] == datetime(2023, 9, 20).isoformat()
