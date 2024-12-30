import asyncio
from datetime import date

from sqlalchemy import String, ForeignKey, UniqueConstraint, BigInteger, Boolean, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column

from conf import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME
from logs import custom_logger

ALCHEMY_ECHO = False
DESCRIBE = False


class Base(DeclarativeBase, AsyncAttrs):
    """Base model"""


class Chat(Base):
    __tablename__ = 'chats'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    schedule: Mapped[bool] = mapped_column(Boolean, default=False)
    less: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text('true'))

    directions: Mapped[list['Direction']] = relationship(back_populates='chat', cascade='all, delete-orphan')


class FlightBase(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    src: Mapped[str] = mapped_column(String(3))
    dst: Mapped[str] = mapped_column(String(3))
    travel_date: Mapped[date] = mapped_column()
    price: Mapped[int] = mapped_column()


class Direction(FlightBase):
    __tablename__ = 'directions'

    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id'))

    chat: Mapped['Chat'] = relationship(back_populates='directions')

    __table_args__ = (
        UniqueConstraint('src', 'dst', 'chat_id', name='uix_src_dst_chat_id'),
    )


class Flight(FlightBase):
    __tablename__ = 'flights'
    __table_args__ = (
        UniqueConstraint('src', 'dst', 'travel_date', name='uix_src_dst_date'),
    )

    def __hash__(self) -> int:
        return hash(f'{self.src}{self.dst}{self.travel_date.strftime("%-d.%-m.%Y")}')


connection_string = f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

async_engine = create_async_engine(
    connection_string,
    pool_pre_ping=True, echo=ALCHEMY_ECHO
)
ASession = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
)


async def main():
    if DESCRIBE:
        from sqlalchemy.sql.ddl import CreateTable
        from sqlalchemy.dialects.postgresql import dialect
        for table in Base.metadata.sorted_tables:
            create_table_sql = f'{(CreateTable(table).compile(dialect=dialect()))}'
            custom_logger.ingo(create_table_sql)
    else:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


if __name__ == '__main__':
    asyncio.run(main())