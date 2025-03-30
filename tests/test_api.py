from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.api import app
from db import Direction, Chat


@pytest.fixture
async def seed_data(session):
    chat1 = Chat(tg_id=123, id=1)
    chat2 = Chat(tg_id=456, id=2)
    session.add_all([chat1, chat2])
    await session.commit()

    direction1 = Direction(src='LAX', dst='JFK', travel_date=date(2023, 12, 25), price=300, chat_id=1, id=1)
    direction2 = Direction(src='SFO', dst='ORD', travel_date=date(2023, 12, 26), price=350, chat_id=2, id=2)
    session.add_all([direction1, direction2])
    await session.commit()


@pytest.mark.asyncio
async def test_directions_endpoint(session, seed_data, monkeypatch, redis_mock):
    """
    Test the `/directions` endpoint to ensure it returns directions that belong to the authorized user.
    """
    client = TestClient(app)

    # Obtain a token
    response = client.post('/auth/token', data={'username': '123', 'password': 'valid_otp'})
    assert response.status_code == 200
    token = response.json()['access_token']

    # Test the /directions endpoint
    response = client.get('/directions', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    directions = response.json()
    assert len(directions) == 1
    assert directions[0]['src'] == 'LAX'
    assert directions[0]['dst'] == 'JFK'
    assert directions[0]['travel_date'] == '2023-12-25T00:00:00'
    assert directions[0]['price'] == 300
    assert directions[0]['chat_id'] == 1
    assert directions[0]['id'] == 1
