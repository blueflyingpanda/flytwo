import asyncio
import json
import logging
from os import environ

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram import Router
from aiogram.filters import Command

BOT_TOKEN = environ.get('BOT_TOKEN')
CLOUD_FUNC_URL = environ.get('CLOUD_FUNC_URL')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()


@router.message(Command(commands=['help']))
async def cmd_help(message: types.Message):
    chat_id = message.chat.id
    await message.reply(f'Your chat ID is: {chat_id}')

@router.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    await message.reply('Manual launch started ...')
    async with aiohttp.ClientSession() as session:
        async with session.post(CLOUD_FUNC_URL):
            await message.reply('Manual launch finished!')

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
