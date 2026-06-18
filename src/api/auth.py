import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import parse_qsl

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from api.models import JwtPayload, TelegramAuthRequest, Token, User
from cache import redis_client
from conf import BOT_TOKEN, JWT_ACCESS_TOKEN_EXPIRE, JWT_SECRET
from dal import DataAccessLayer
from logs import logger

JWT_ALGORITHM = 'HS256'
TG_INITDATA_MAX_AGE = 86400  # seconds an initData payload stays valid

router = APIRouter(prefix='/auth', tags=['Authentication'])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/token')


def _issue_token(chat_id: str) -> Token:
    expire = datetime.now(UTC) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE)
    payload = JwtPayload(chat_id=chat_id, expire=expire)
    access_token = jwt.encode(jsonable_encoder(payload.model_dump()), JWT_SECRET, JWT_ALGORITHM)
    return Token(access_token=access_token, token_type='bearer')


def _verify_telegram_init_data(init_data: str) -> int:
    """Validate Telegram Mini App initData and return the authenticated tg user id.

    See https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Malformed init data')

    received_hash = parsed.pop('hash', None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing hash')

    data_check_string = '\n'.join(f'{k}={parsed[k]}' for k in sorted(parsed))
    secret_key = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid init data signature')

    auth_date = int(parsed.get('auth_date', 0))
    if datetime.now(UTC).timestamp() - auth_date > TG_INITDATA_MAX_AGE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Init data expired')

    try:
        user = json.loads(parsed['user'])
        return int(user['id'])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing user in init data')


async def get_current_user(access_token: str = Depends(oauth2_scheme)) -> User:
    data = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    payload = JwtPayload(**data)

    if payload.expire < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Expired token')

    chat = await DataAccessLayer.get_chat(int(payload.chat_id))

    if not chat:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')

    return User(chat_id=chat.tg_id)


@router.post('/token')
async def token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    chat = await DataAccessLayer.get_chat(tg_id=int(form_data.username))

    if not chat:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username')

    chat_id = str(chat.tg_id)

    otp = ''
    cache_key = f'otp:{chat_id}'

    async with redis_client() as cache:
        otp = await cache.getdel(cache_key)

    logger.info('key |%s|; otp |%s|, pass |%s|', cache_key, otp.decode() if otp else otp, form_data.password)

    if not otp or otp.decode() != form_data.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or missing code')

    return _issue_token(chat_id)


@router.post('/telegram')
async def telegram(request: TelegramAuthRequest) -> Token:
    """Authenticate a Telegram Mini App user via signed initData.

    Opening the Mini App implies an active chat, so the chat is created if absent
    (equivalent to /start in the bot).
    """
    tg_id = _verify_telegram_init_data(request.init_data)
    await DataAccessLayer.create_chat(tg_id=tg_id)
    return _issue_token(str(tg_id))
