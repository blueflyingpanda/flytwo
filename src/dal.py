from typing import Any

from sqlalchemy import select, RowMapping, Row
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import Chat, ASession, Direction


class DataAccessLayer:
    def __init__(self, model: Any, session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by(self, **kwargs) -> RowMapping:
        stmt = select(self.model).filter_by(**kwargs)
        result = await self.session.execute(stmt)
        instance = result.scalars().first()

        return instance

    async def get_or_create(
            self, defaults: dict[str, Any] | None = None, **kwargs
    ) -> tuple[Row | RowMapping, bool]:

        model = self.model
        session = self.session

        stmt = select(model).filter_by(**kwargs)
        result = await session.execute(stmt)
        instance = result.scalars().first()

        if instance:
            return instance, False  # Object found

        instance = model(**kwargs, **(defaults or {}))
        session.add(instance)

        try:
            await session.commit()
            return instance, True  # Object created
        except IntegrityError:
            await session.rollback()
            # In case another process created the instance, try fetching it again
            result = await session.execute(stmt)
            instance = result.scalars().first()
            return instance, False  # Object found after race condition

    async def delete(self, **kwargs) -> bool:
        session = self.session

        stmt = select(self.model).filter_by(**kwargs)
        result = await session.execute(stmt)
        instance = result.scalars().first()

        if instance:
            await session.delete(instance)
            await session.commit()
            return True  # Successfully deleted

        return False  # No record found to delete


    @staticmethod
    async def get_directions_by_chats(chat_ids: list[int] | None = None) -> dict[Chat, list[Direction]]:

        async with ASession() as session:
            stmt = select(Chat).options(selectinload(Chat.directions))

            if chat_ids is not None:
                stmt = stmt.where(Chat.tg_id.in_(chat_ids))

            result = await session.execute(stmt)
            chats = result.scalars().all()

            directions_by_chats = {chat: chat.directions for chat in chats}

        return directions_by_chats