from datetime import date

from fastapi import FastAPI

from dal import DataAccessLayer
from fly_client.client import FlyoneClient

app = FastAPI()


@app.get('/ping')
async def ping():
    return {'ping': 'pong'}

@app.get('/price-history/{src}/{dst}')
async def price_history(src: str, dst: str, dt: date | None = None):
    return await DataAccessLayer.get_direction_price_history(src, dst, dt)

@app.get('/airports')
async def price_history():
    """Proxy endpoint to fetch airports from Flyone API."""
    fc = FlyoneClient()
    return await fc.airport_by_code
