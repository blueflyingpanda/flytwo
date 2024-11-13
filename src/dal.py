from datetime import date
from typing import Any

from sqlalchemy import select, RowMapping, Row, update, case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from db import Chat, ASession, Direction


class DBUtils:

    @staticmethod
    async def upsert(
            model, defaults: dict[str, Any] | None = None, **kwargs
    ) -> tuple[Row | RowMapping, bool]:

        async with ASession() as session:

            stmt = select(model).filter_by(**kwargs)
            result = await session.execute(stmt)
            instance = result.scalars().first()

            if instance:
                for key, value in defaults.items():
                    setattr(instance, key, value)
                await session.commit()
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

    @staticmethod
    async def delete(model, **kwargs) -> bool:
        async with ASession() as session:
            stmt = select(model).filter_by(**kwargs)
            result = await session.execute(stmt)
            instance = result.scalars().first()

        if instance:
            await session.delete(instance)
            await session.commit()
            return True  # Successfully deleted

        return False  # No record found to delete


class DataAccessLayer:

    @staticmethod
    async def get_chat(tg_id: int) -> Chat | None:
        async with ASession() as session:
            stmt = select(Chat).filter_by(tg_id=tg_id)
            result = await session.execute(stmt)
            instance = result.scalars().first()

        return instance

    @staticmethod
    async def create_chat(tg_id: int) -> [Chat, bool]:
        return await DBUtils.upsert(Chat, tg_id=tg_id)

    @staticmethod
    async def remove_chat(tg_id: int) -> [Chat, bool]:
        return await DBUtils.delete(Chat, tg_id=tg_id)

    @staticmethod
    async def create_direction(chat_id: int, src: str, dst: str, price: int, travel_date: date) -> [Direction, bool]:
        return await DBUtils.upsert(
            Direction,
            chat_id=chat_id, src=src, dst=dst,
            defaults={'travel_date': travel_date, 'price': price}
        )

    @staticmethod
    async def remove_direction(chat_id: int, src: str, dst: str) -> [Direction, bool]:
        return await DBUtils.delete(Direction, chat_id=chat_id, src=src, dst=dst)

    @staticmethod
    async def toggle_schedule(tg_id: int) -> bool | None:
        async with ASession() as session:
            stmt = (
                update(Chat)
                .filter_by(tg_id=tg_id)
                .values(schedule=case(
                        (Chat.schedule == True, False),
                        else_=True
                    )
                )
                .returning(Chat.schedule)
            )
            result = await session.execute(stmt)
            updated_schedule = result.scalar_one_or_none()

            await session.commit()

            return updated_schedule

    @staticmethod
    async def get_directions_by_chats(chat_ids: list[int] | None = None) -> dict[Chat, list[Direction]]:

        async with ASession() as session:
            stmt = select(Chat).options(selectinload(Chat.directions))

            if chat_ids is not None:
                stmt = stmt.where(Chat.tg_id.in_(chat_ids))
            else:
                stmt = stmt.where(Chat.schedule == True)

            result = await session.execute(stmt)
            chats = result.scalars().all()

            directions_by_chats = {chat: chat.directions for chat in chats}

        return directions_by_chats