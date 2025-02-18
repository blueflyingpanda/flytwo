import asyncio
import json
import logging
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from conf import BOT_TOKEN, CLOUD_FUNC_URL
from dal import DataAccessLayer
from fly_client.client import FlyoneClient
from notifier import TgBotNotifier
from parser import UrlParser
from plotter import Plotter

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()


@router.message(Command(commands=['help']))
async def cmd_help(message: types.Message):
    help_text = (
        'Here are the available commands:\n\n'
        '/start - Start the bot.\n'
        'Usage: Just type /start\n\n'
        '/stop - Stop the bot.\n'
        'Usage: Just type /stop\n\n'
        '/add <src> <dst> <travel_date> <price> OR /add <link> <price> - Add a travel direction.\n'
        'Example: /add RMO EVN 15.10.2024 300\n'
        'Note: src and dst should be 3-letter airport codes. The price must be a whole number of EUR.\n\n'
        '/remove <src> <dst> OR /remove <link> - Remove a travel direction.\n'
        'Example: /remove RMO EVN\n'
        'Note: src and dst should be 3-letter airport codes.\n\n'
        '/go - Manually launch the bot.\n'
        'Usage: Just type /go\n\n'
        '/schedule - Toggles scheduling setting for the chat. If ON, triggers the bot by schedule to check prices of '
        'selected flights\n'
        'Usage: Just type /schedule\n\n'
        '/less - Toggles silence mode for the chat. If ON, messages will be sent only on changes.\n'
        'Usage: Just type /less\n\n'
        '/airports - lists all available airports by their codes.\n'
        'Usage: Just type /airports\n\n'
        '/directions - lists all directions related to the chat.\n'
        'Usage: Just type /directions\n\n'
        '/stats - draws the chart of price changes for certain direction.\n'
        'Usage: /stats <src> <dst>\n\n'
    )
    await message.reply(help_text)


@router.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    _, created = await DataAccessLayer.create_chat(tg_id=message.chat.id)

    if created:
        await message.reply(f'Bot started! Use /help for more info.')
    else:
        await message.reply(f'Bot is already running! Use /help for more info.')


@router.message(Command(commands=['stop']))
async def cmd_stop(message: types.Message):
    deleted = await DataAccessLayer.remove_chat(tg_id=message.chat.id)

    if deleted:
        await message.reply(f'Bot stopped!')
    else:
        await message.reply(f'Bot is already stopped.')


@router.message(Command(commands=['add']))
async def cmd_add(message: types.Message):
    command_parts = message.text.split()

    if len(command_parts) == 3:
        src, dst, travel_date_str = UrlParser.parse(command_parts[1])
        command_parts = [command_parts[0], src, dst, travel_date_str, command_parts[2]]

    if len(command_parts) != 5:
        await message.reply('Usage: /add <src> <dst> <travel_date> <price> OR /add <link> <price>')
        return

    _, src, dst, travel_date_str, price_str = command_parts

    src = src.upper()
    dst = dst.upper()

    if src == dst:
        await message.reply('Source cannot be the same as destination.')
        return

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
        return

    fc = FlyoneClient()
    airport_by_code = await fc.airport_by_code

    if src not in airport_by_code or dst not in airport_by_code:
        await message.reply('Airport not supported. Find supported airports using /airports')
        return

    chat = await DataAccessLayer.get_chat(tg_id=message.chat.id)

    if chat is None:
        await message.reply('Bot was not started yet!')
        return

    direction, created = await DataAccessLayer.create_direction(
        chat_id=chat.id, src=src, dst=dst, travel_date=travel_date, price=price
    )

    if created:
        await message.reply('New direction has been added.')
    else:
        await message.reply('Direction has been updated.')


@router.message(Command(commands=['remove']))
async def cmd_remove(message: types.Message):
    command_parts = message.text.split()

    if len(command_parts) == 2:
        src, dst, _ = UrlParser.parse(command_parts[1])
        command_parts = [command_parts[0], src, dst]

    if len(command_parts) != 3:
        await message.reply('Usage: /remove <src> <dst>')
        return

    _, src, dst = command_parts

    src = src.upper()
    dst = dst.upper()

    if src == dst:
        await message.reply('Source cannot be the same as destination.')
        return

    if any(filter(lambda elem: len(elem) != 3, (src, dst))):
        await message.reply('Invalid airport code! Should be 3 letters.')

    chat = await DataAccessLayer.get_chat(tg_id=message.chat.id)

    if chat is None:
        await message.reply('Bot was not started yet!')
        return

    deleted = await DataAccessLayer.remove_direction(chat_id=chat.id, src=src, dst=dst)

    if deleted:
        await message.reply(f'Direction has been removed.')
    else:
        await message.reply(f'Direction was not found.')


@router.message(Command(commands=['go']))
async def cmd_go(message: types.Message):
    await message.reply('Manual launch started ...')
    async with aiohttp.ClientSession() as session:
        async with session.post(CLOUD_FUNC_URL, json={'chat_id': message.chat.id, 'manual': True}):
            await message.reply('Manual launch finished!')


@router.message(Command(commands=['schedule']))
async def cmd_schedule(message: types.Message):
    schedule = await DataAccessLayer.toggle_schedule(tg_id=message.chat.id)

    if schedule is None:
        await message.reply('Bot was not started yet!')
        return

    await message.reply(f'Schedule: {"ON" if schedule else "OFF"}')


@router.message(Command(commands=['less']))
async def cmd_less(message: types.Message):
    schedule = await DataAccessLayer.toggle_less(tg_id=message.chat.id)

    if schedule is None:
        await message.reply('Bot was not started yet!')
        return

    await message.reply(f'Silent mode: {"ON" if schedule else "OFF"}')


@router.message(Command(commands=['directions']))
async def cmd_directions(message: types.Message):
    directions_by_chats = await DataAccessLayer.get_directions_by_chats([message.chat.id])

    if not directions_by_chats:
        await message.reply('Bot was not started yet!')
        return

    chat, directions = next(iter(directions_by_chats.items()))

    if not directions:
        await message.reply('No directions found.')

    fc = FlyoneClient()
    airport_by_code = await fc.airport_by_code

    msgs = []

    for direction in directions:
        msg = await TgBotNotifier.form_direction_info(direction, airport_by_code)
        msgs.append(msg)

    notifier = TgBotNotifier(chat_id=message.chat.id)
    await notifier.send_msgs(msgs)


@router.message(Command(commands=['airports']))
async def cmd_airports(message: types.Message):
    fc = FlyoneClient()

    airport_by_code = await fc.airport_by_code
    msgs = [
        f'{code} [{airport.name}] |{airport.country}|'
        for code in sorted(iter(airport_by_code.keys())) if (airport := airport_by_code[code])
    ]
    notifier = TgBotNotifier(chat_id=message.chat.id)
    await notifier.send_msgs(['\n'.join(msgs)])

@router.message(Command(commands=['stats']))
async def cmd_stats(message: types.Message):
    command_parts = message.text.split()

    if len(command_parts) != 3:
        await message.reply('Usage: /stats <src> <dst>')
        return

    _, src, dst = command_parts

    src = src.upper()
    dst = dst.upper()

    if src == dst:
        await message.reply('Source cannot be the same as destination.')
        return

    price_history = await DataAccessLayer.get_direction_price_history(src, dst)

    buffer = await Plotter.plot_price_history(src, dst, price_history)

    chart_image = BufferedInputFile(buffer.read(), filename='price_chart.png')
    buffer.close()

    await message.answer_photo(photo=chart_image, caption=f'Price History for {src} → {dst}')


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
