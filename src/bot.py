import asyncio
import json
import logging
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram import Router
from aiogram.filters import Command

from conf import BOT_TOKEN, CLOUD_FUNC_URL
from dal import DataAccessLayer
from db import ASession, Chat, Direction

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()


@router.message(Command(commands=['help']))
async def cmd_help(message: types.Message):
    help_text = (
        "Here are the available commands:\n\n"
        "/start - Start the bot.\n"
        "Usage: Just type /start\n\n"
        "/stop - Stop the bot.\n"
        "Usage: Just type /stop\n\n"
        "/subscribe <src> <dst> <travel_date> <price> - Subscribe to a travel direction.\n"
        "Example: /subscribe RMO EVN 15.10.2024 300\n"
        "Note: src and dst should be 3-letter airport codes. The price must be a whole number of EUR.\n\n"
        "/unsubscribe <src> <dst> - Unsubscribe from a travel direction.\n"
        "Example: /unsubscribe RMO EVN\n"
        "Note: src and dst should be 3-letter airport codes.\n\n"
        "/trigger - Manually trigger the bot. It triggers by schedule at 10:00, 16:00, 22:00 GMT+3\n"
        "Usage: Just type /trigger\n"
    )
    await message.reply(help_text)


@router.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    async with ASession() as session:
        dal = DataAccessLayer(Chat, session)
        _, created = await dal.get_or_create(tg_id=message.chat.id)

    if created:
        await message.reply(f'Bot started! Use /help for more info.')
    else:
        await message.reply(f'Bot is already running! Use /help for more info.')


@router.message(Command(commands=['stop']))
async def cmd_stop(message: types.Message):
    async with ASession() as session:
        dal = DataAccessLayer(Chat, session)
        deleted = await dal.delete(tg_id=message.chat.id)

    if deleted:
        await message.reply(f'Bot stopped!')
    else:
        await message.reply(f'Bot is already stopped.')


@router.message(Command(commands=['subscribe']))
async def cmd_subscribe(message: types.Message):
    command_parts = message.text.split()

    if len(command_parts) != 5:
        await message.reply('Usage: /subscribe <src> <dst> <travel_date> <price>')
        return

    _, src, dst, travel_date_str, price_str = command_parts

    try:
        travel_date = datetime.strptime(travel_date_str, "%d.%m.%Y").date()
    except ValueError:
        await message.reply('Invalid travel date format. Please use DD.MM.YYYY')
        return

    try:
        price = int(price_str)
        if price <= 0:
            raise ValueError('Price must be a positive whole number.')
    except ValueError:
        await message.reply('Invalid price. Please provide a whole positive number.')
        return

    if any(filter(lambda elem: len(elem) != 3, (src, dst))):
        await message.reply('Invalid airport code! Should be 3 letters.')

    async with ASession() as session:
        dal_chat = DataAccessLayer(Chat, session)
        chat = await dal_chat.get_by(tg_id=message.chat.id)

        if chat is None:
            await message.reply('Bot was not started yet!')
            return

        dal_dir = DataAccessLayer(Direction, session)
        direction, created = await dal_dir.get_or_create(
            chat_id=chat.id, src=src.upper(), dst=dst.upper(),
            defaults={'travel_date': travel_date, 'price': price}
        )

        if created:
            await message.reply('New direction has been added.')
        else:
            direction.travel_date = travel_date
            direction.price = price
            await session.commit()
            await message.reply('Direction has been updated.')


@router.message(Command(commands=['unsubscribe']))
async def cmd_unsubscribe(message: types.Message):
    command_parts = message.text.split()

    if len(command_parts) != 3:
        await message.reply('Usage: /unsubscribe <src> <dst>')
        return

    _, src, dst = command_parts

    if any(filter(lambda elem: len(elem) != 3, (src, dst))):
        await message.reply('Invalid airport code! Should be 3 letters.')

    async with ASession() as session:
        dal_chat = DataAccessLayer(Chat, session)
        chat = await dal_chat.get_by(tg_id=message.chat.id)

        if chat is None:
            await message.reply('Bot was not started yet!')
            return

        dal_dir = DataAccessLayer(Direction, session)
        deleted = await dal_dir.delete(chat_id=chat.id, src=src.upper(), dst=dst.upper())

    if deleted:
        await message.reply(f'Direction has been removed.')
    else:
        await message.reply(f'Direction was not found.')


@router.message(Command(commands=['trigger']))
async def cmd_trigger(message: types.Message):
    await message.reply('Manual launch started ...')
    async with aiohttp.ClientSession() as session:
        async with session.post(CLOUD_FUNC_URL, json={'chat_id': message.chat.id}):
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
