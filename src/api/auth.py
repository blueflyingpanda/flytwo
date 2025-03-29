from datetime import datetime, timezone, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from cache import redis_client
from conf import JWT_ACCESS_TOKEN_EXPIRE, JWT_SECRET
from dal import DataAccessLayer

JWT_ALGORITHM = 'HS256'

router = APIRouter(prefix='/auth', tags=['Authentication'])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/token')


class User(BaseModel):
    chat_id: str


class JwtPayload(BaseModel):
    chat_id: str
    expire: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


async def get_current_user(access_token: str = Depends(oauth2_scheme)) -> User:
    data = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    payload = JwtPayload(**data)

    if payload.expire < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Expired token')

    chat = await DataAccessLayer.get_chat(int(payload.chat_id))

    if not chat:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')

    return User(chat_id=str(chat.tg_id))


@router.post('/token')
async def token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    chat = await DataAccessLayer.get_chat(tg_id=int(form_data.username))

    if not chat:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid username')

    chat_id = str(chat.tg_id)

    async with redis_client() as cache:
        otp = await cache.getdel(f'otp:{chat_id}')

    if not otp or otp.decode() != form_data.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or missing code')

    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE)
    payload = JwtPayload(chat_id=chat_id, expire=expire)
    access_token = jwt.encode(jsonable_encoder(payload.model_dump()), JWT_SECRET, JWT_ALGORITHM)

    return Token(access_token=access_token, token_type='bearer')
