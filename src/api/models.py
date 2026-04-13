from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class Ping(BaseModel):
    ping: str
    pong: str


class NotifyRequest(BaseModel):
    chat_id: int | None = None
    manual: bool = False


class User(BaseModel):
    chat_id: str


class UserDirection(BaseModel):
    src: str
    dst: str
    travel_date: date
    price: int

    model_config = ConfigDict(
        from_attributes=True
    )  # allows UserDirection.model_validate() on db.Direction instance from SqlAlchemy


class JwtPayload(BaseModel):
    chat_id: str
    expire: datetime


class Token(BaseModel):
    access_token: str
    token_type: str
