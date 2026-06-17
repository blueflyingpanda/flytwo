from fastapi import HTTPException, status

from dal import DataAccessLayer
from db import Chat


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


async def get_chat_or_404(tg_id: int) -> Chat:
    chat = await DataAccessLayer.get_chat(tg_id=tg_id)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Chat not found. Start the bot first.')
    return chat
