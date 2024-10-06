import asyncio
import json
import logging
from os import environ

from aiogram import Bot, Dispatcher, types
from aiogram import Router
from aiogram.filters import Command

BOT_TOKEN = environ.get('BOT_TOKEN')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()


@router.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    chat_id = message.chat.id
    await message.reply(f"Your chat ID is: {chat_id}")

dp.include_router(router)


async def handler(event, context):

    body = json.loads(event['body'])
    update = types.Update(**body)
    await dp.feed_update(bot, update)

    return {
        'statusCode': 200,
        'body': 'success'
    }


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
