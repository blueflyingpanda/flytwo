from datetime import date, datetime, UTC
from typing import Any, Type

from sqlalchemy import select, RowMapping, Row, update, case, delete, and_, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from db import Chat, ASession, Direction, Flight, FlightBase
from fly_client.client import Flight as FetchedFlight
from logs import custom_logger


class DBUtils:

    @staticmethod
    async def upsert(
            model, defaults: dict[str, Any] | None = None, **kwargs
    ) -> tuple[Row | RowMapping, bool]:

        defaults = defaults or {}

        async with ASession() as session:

            stmt = select(model).filter_by(**kwargs)
            result = await session.execute(stmt)
            instance = result.scalars().first()

            if instance:
                for key, value in defaults.items():
                    setattr(instance, key, value)
                await session.commit()
                return instance, False  # Object found

            instance = model(**kwargs, **defaults)
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
    async def _toggle(tg_id: int, field_name: str) -> bool | None:
        """field_name: bool that changes its value to the opposite"""
        async with ASession() as session:
            field = getattr(Chat, field_name)
            stmt = (
                update(Chat)
                .filter_by(tg_id=tg_id)
                .values(**{field_name: case((field == True, False), else_=True)})
                .returning(field)
            )
            result = await session.execute(stmt)
            updated_value = result.scalar_one_or_none()
            await session.commit()
            return updated_value

    @staticmethod
    async def toggle_schedule(tg_id: int) -> bool | None:
        return await DataAccessLayer._toggle(tg_id, 'schedule')

    @staticmethod
    async def toggle_less(tg_id: int) -> bool | None:
        return await DataAccessLayer._toggle(tg_id, 'less')

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

    @staticmethod
    async def cleanup_outdated(model: Type[FlightBase]):
        current_date = datetime.now(UTC).date()

        async with ASession() as session:
            stmt = delete(model).where(model.travel_date < current_date)
            result = await session.execute(stmt)
            await session.commit()

            custom_logger.info(f'{result.rowcount} outdated {model.__tablename__} deleted')

    @staticmethod
    async def get_flights(fetched_flights: list[FetchedFlight]) -> list[Flight]:

        async with ASession() as session:
            filters = [
                and_(
                    Flight.src == flight.from_airport.code,
                    Flight.dst == flight.to_airport.code,
                    Flight.travel_date == datetime.strptime(flight.travel_date, '%d.%m.%Y').date()
                )
                for flight in fetched_flights
            ]

            stmt = select(Flight).where(or_(*filters))
            result = await session.execute(stmt)

            flights = result.scalars().all()

        return flights

    @staticmethod
    async def add_flights(fetched_flights: list[FetchedFlight]):
        async with ASession() as session:
            new_flight_data = [
                {
                    'src': fetched_flight.from_airport.code,
                    'dst': fetched_flight.to_airport.code,
                    'travel_date': datetime.strptime(fetched_flight.travel_date, '%d.%m.%Y').date(),
                    'price': 0  # in order to detect flights in FlightsChangeDetector
                }
                for fetched_flight in fetched_flights
            ]

            if new_flight_data:
                stmt = insert(Flight).values(new_flight_data)
                # specific for postgres
                stmt = stmt.on_conflict_do_nothing(index_elements=['src', 'dst', 'travel_date'])

                result = await session.execute(stmt)
                await session.commit()

                custom_logger.info(f'{result.rowcount} new flights inserted')

    @staticmethod
    async def update_flights(updated_price_by_flight: list[dict[str, int]]):

        async with ASession() as session:
            flight_ids = [item['id'] for item in updated_price_by_flight]

            result = await session.execute(
                select(Flight).where(Flight.id.in_(flight_ids))
            )
            flights = {flight.id: flight for flight in result.scalars().all()}

            for flight_data in updated_price_by_flight:
                flight_id = flight_data['id']
                new_price = flight_data['price']

                flight = flights.get(flight_id)

                # so that orm detects changes in column
                flight.history = flight.history + [{'price': new_price, 'dt': datetime.now().isoformat()}]
                flight.price = new_price

            await session.commit()

            custom_logger.info(f'{len(updated_price_by_flight)} flights updated')

    @staticmethod
    async def get_direction_price_history(src: str, dst: str) -> dict[date, list[dict[str, int]]]:
        async with ASession() as session:
            stmt = select(Flight).where(Flight.src == src, Flight.dst == dst)
            result = await session.execute(stmt)
            flights = result.scalars().all()

            price_history_by_date = {flight.travel_date: flight.history for flight in flights}

            return price_history_by_date
