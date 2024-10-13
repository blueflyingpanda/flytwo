import asyncio

from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship

from conf import DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME


ALCHEMY_ECHO = False
DESCRIBE = False


class Base(DeclarativeBase, AsyncAttrs):
    """Base model"""


class Chat(Base):
    __tablename__ = 'chats'

    id: int = Column(Integer, primary_key=True)
    chat_id: str = Column(String, nullable=False, unique=True)

    directions = relationship('Direction', back_populates='chat')


class Direction(Base):
    __tablename__ = 'directions'

    id: int = Column(Integer, primary_key=True)
    src: str = Column(String, nullable=False)
    dst: str = Column(String, nullable=False)
    travel_date: Date = Column(Date, nullable=False)
    price: int = Column(Integer, nullable=False)
    chat_id: int = Column(Integer, ForeignKey('chats.id'), nullable=False)
    msg_hash: str = Column(String, nullable=False, default='')

    chat = relationship('Chat', back_populates='directions')


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
            print(create_table_sql)
    else:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


if __name__ == '__main__':
    asyncio.run(main())