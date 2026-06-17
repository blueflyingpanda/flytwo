from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Ping(BaseModel):
    ping: str
    pong: str


class NotifyRequest(BaseModel):
    chat_id: int | None = None
    manual: bool = False


class User(BaseModel):
    chat_id: int


class UserDirection(BaseModel):
    src: str
    dst: str
    travel_date: date
    price: int
    notify_on_decrease: bool | None = None
    threshold: int = 0

    model_config = ConfigDict(
        from_attributes=True
    )  # allows UserDirection.model_validate() on db.Direction instance from SqlAlchemy


class JwtPayload(BaseModel):
    chat_id: str
    expire: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class TelegramAuthRequest(BaseModel):
    """Raw initData string handed over by the Telegram Mini App runtime."""

    init_data: str


class ChatInfo(BaseModel):
    chat_id: str
    schedule: str
    less: bool
    last_notified: datetime | None
    premium: bool
    currency: str
    directions_count: int


class CreateDirectionRequest(BaseModel):
    """Either provide src/dst/travel_date explicitly, or a supported airline link."""

    src: str | None = None
    dst: str | None = None
    travel_date: date | None = None
    price: int
    link: str | None = None


class NotifyMode(StrEnum):
    ANY = 'any'
    INCREASE = 'increase'
    DECREASE = 'decrease'


class UpdateDirectionRequest(BaseModel):
    notify: NotifyMode | None = None
    threshold: int | None = None


class MessageResponse(BaseModel):
    detail: str
    created: bool | None = None


class ScheduleRequest(BaseModel):
    """Human friendly pattern, e.g. '4h', '6pm', '8am-11pm 2h'."""

    pattern: str


class ScheduleResponse(BaseModel):
    schedule: str  # rrule string, or '' when disabled


class SilentResponse(BaseModel):
    less: bool


class CurrencyRequest(BaseModel):
    currency: str


class CurrencyInfo(BaseModel):
    code: str
    symbol: str | None = None


class ConvertResponse(BaseModel):
    amount: int
    from_currency: str
    to_currency: str
    result: int


class PromoRequest(BaseModel):
    src: str
    travel_date: date
    price: int


class PromoFare(BaseModel):
    src: str
    dst: str
    price: int
    currency: str
    airline: str
    travel_date: date
