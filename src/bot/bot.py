import asyncio
from datetime import datetime
from random import randint

import aiohttp
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from bot.notifier import TgBotNotifier
from bot.parser import ScheduleParser, UrlParser
from cache import redis_client
from client.client import FlyoneClient
from conf import API_URL, BOT_SECRET, BOT_TOKEN
from dal import DataAccessLayer
from plotter import MissingPriceHistoryError, Plotter

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
        '/schedule [pattern] - Toggle scheduling on/off, or set a check frequency.\n'
        'Usage: /schedule to toggle, or with a pattern:\n'
        '  1h            every hour (default)\n'
        '  Nh            every N hours\n'
        '  6pm           daily at 6pm\n'
        '  8am-11pm      every hour from 8am to 11pm\n'
        '  8am-11pm 2h   every 2 hours from 8am to 11pm\n\n'
        '/less - Toggles silence mode for the chat. If ON, messages will be sent only on changes.\n'
        'Usage: Just type /less\n\n'
        '/airports - lists all available airports by their codes.\n'
        'Usage: Just type /airports\n\n'
        '/directions - lists all directions related to the chat.\n'
        'Usage: Just type /directions\n\n'
        '/stats - draws the chart of price changes for certain direction.\n'
        'Usage: /stats <src> <dst> OR /stats <src> <dst> <date>\n\n'
        '/auth - returns chat id and one-time code for authorization in API.\n'
        'Usage: Just type /auth\n\n'
        '/notify <src> <dst> [+|-] - Set notification preference for a direction.\n'
        'Example: /notify RMO EVN -\n'
        'Note: + for price increase only, - for price decrease only, omit for any change.\n\n'
        '/threshold <src> <dst> <value> - Set minimum price change to trigger a notification.\n'
        'Example: /threshold RMO EVN 20\n'
        'Note: value must be a non-negative whole number of EUR. Default is 0 (notify on any change).\n\n'
    )
    await message.reply(help_text)


@router.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    _, created = await DataAccessLayer.create_chat(tg_id=message.chat.id)

    if created:
        await message.reply('Bot started! Use /help for more info.')
    else:
        await message.reply('Bot is already running! Use /help for more info.')


@router.message(Command(commands=['stop']))
async def cmd_stop(message: types.Message):
    deleted = await DataAccessLayer.remove_chat(tg_id=message.chat.id)

    if deleted:
        await message.reply('Bot stopped!')
    else:
        await message.reply('Bot is already stopped.')


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
        travel_date = datetime.strptime(travel_date_str, '%d.%m.%Y').date()
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

    _, created = await DataAccessLayer.create_direction(
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
        await message.reply('Direction has been removed.')
    else:
        await message.reply('Direction was not found.')


@router.message(Command(commands=['go']))
async def cmd_go(message: types.Message):
    await message.reply('Manual launch started ...')
    async with (
        aiohttp.ClientSession() as session,
        session.post(
            f'{API_URL}/notify',
            json={'chat_id': message.chat.id, 'manual': True},
            headers={'x-notify-secret': BOT_SECRET},
        ),
    ):
        ...
    await message.reply('Manual launch finished!')


@router.message(Command(commands=['schedule']))
async def cmd_schedule(message: types.Message):
    command_parts = message.text.split(maxsplit=1)

    if len(command_parts) == 1:
        schedule = await DataAccessLayer.toggle_schedule(tg_id=message.chat.id)

        if schedule is None:
            await message.reply('Bot was not started yet!')
            return

        await message.reply(f'Schedule: {"ON" if schedule else "OFF"}')
        return

    rrule = ScheduleParser.parse(command_parts[1])

    if rrule is None:
        await message.reply(
            'Invalid format. Examples:\n'
            '  1h          every hour\n'
            '  4h          every 4 hours\n'
            '  6pm         daily at 6pm\n'
            '  8am-11pm    every hour from 8am to 11pm\n'
            '  8am-11pm 2h every 2 hours from 8am to 11pm'
        )
        return

    updated = await DataAccessLayer.set_schedule_rrule(tg_id=message.chat.id, rrule=rrule)

    if not updated:
        await message.reply('Bot was not started yet!')
        return

    await message.reply(f'Schedule enabled: {command_parts[1].strip()}')


@router.message(Command(commands=['less']))
async def cmd_less(message: types.Message):
    schedule = await DataAccessLayer.toggle_less(tg_id=message.chat.id)

    if schedule is None:
        await message.reply('Bot was not started yet!')
        return

    await message.reply(f'Silent mode: {"ON" if schedule else "OFF"}')


@router.message(Command(commands=['auth']))
async def cmd_auth(message: types.Message):
    otp = randint(100000, 999999)  # 6-digit code - one time password

    async with redis_client() as cache:
        await cache.set(f'otp:{message.chat.id}', otp, ex=180)  # code expires in 3 minutes

    await message.reply(f"Chat ID: {message.chat.id}\nCode: {otp}\n\nDon't share this information with anyone!")


@router.message(Command(commands=['directions']))
async def cmd_directions(message: types.Message):
    directions_by_chats = await DataAccessLayer.get_directions_by_chats([message.chat.id])

    if not directions_by_chats:
        await message.reply('Bot was not started yet!')
        return

    _, directions = next(iter(directions_by_chats.items()))

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
        for code in sorted(iter(airport_by_code.keys()))
        if (airport := airport_by_code[code])
    ]
    notifier = TgBotNotifier(chat_id=message.chat.id)
    await notifier.send_msgs(['\n'.join(msgs)])


@router.message(Command(commands=['stats']))
async def cmd_stats(message: types.Message):
    command_parts = message.text.split()

    dt_fmt = '%d.%m.%Y'

    dt = None

    match len(command_parts):
        case 3:
            _, src, dst = command_parts

        case 4:
            _, src, dst, dt = command_parts

        case _:
            await message.reply('Usage: /stats <src> <dst> OR /stats <src> <dst> <date>')
            return

    src = src.upper()
    dst = dst.upper()

    if dt:
        try:
            dt = datetime.strptime(dt, dt_fmt).date()
        except ValueError:
            await message.reply('Invalid date format. Please use DD.MM.YYYY')
            return

    if src == dst:
        await message.reply('Source cannot be the same as destination.')
        return

    price_history = await DataAccessLayer.get_direction_price_history(src, dst, dt)

    try:
        buffer = await Plotter.plot_price_history(src, dst, price_history)
    except MissingPriceHistoryError as e:
        tg_notifier = TgBotNotifier(chat_id=message.chat.id)
        await tg_notifier.send_err(f'{e}')
        return

    chart_image = BufferedInputFile(buffer.read(), filename='price_chart.png')
    buffer.close()

    on_dt = f'on {dt.strftime(dt_fmt)}' if dt else ''

    await message.answer_photo(photo=chart_image, caption=f'Price History for {src} → {dst} {on_dt}'.strip())


@router.message(Command(commands=['notify']))
async def cmd_notify(message: types.Message):
    command_parts = message.text.split()

    if len(command_parts) not in (3, 4):
        await message.reply('Usage: /notify <src> <dst> [+|-]')
        return

    notify_on_decrease: bool | None = None

    if len(command_parts) == 4:
        _, src, dst, symbol = command_parts
        if symbol == '+':
            notify_on_decrease = False
        elif symbol == '-':
            notify_on_decrease = True
        else:
            await message.reply('Invalid symbol. Use + for increase, - for decrease, or omit for any change.')
            return
    else:
        _, src, dst = command_parts

    src = src.upper()
    dst = dst.upper()

    if src == dst:
        await message.reply('Source cannot be the same as destination.')
        return

    if any(filter(lambda elem: len(elem) != 3, (src, dst))):
        await message.reply('Invalid airport code! Should be 3 letters.')
        return

    chat = await DataAccessLayer.get_chat(tg_id=message.chat.id)

    if chat is None:
        await message.reply('Bot was not started yet!')
        return

    updated = await DataAccessLayer.set_notify_on_decrease(
        chat_id=chat.id, src=src, dst=dst, notify_on_decrease=notify_on_decrease
    )

    if not updated:
        await message.reply('Direction not found. Add it first with /add')
        return

    labels = {None: 'any change', False: 'price increase only', True: 'price decrease only'}
    await message.reply(f'Notification preference updated: {labels[notify_on_decrease]}')


@router.message(Command(commands=['threshold']))
async def cmd_threshold(message: types.Message):
    command_parts = message.text.split()

    if len(command_parts) != 4:
        await message.reply('Usage: /threshold <src> <dst> <value>')
        return

    _, src, dst, value_str = command_parts

    src = src.upper()
    dst = dst.upper()

    if src == dst:
        await message.reply('Source cannot be the same as destination.')
        return

    if any(filter(lambda elem: len(elem) != 3, (src, dst))):
        await message.reply('Invalid airport code! Should be 3 letters.')
        return

    try:
        threshold = int(value_str)
        if threshold < 0:
            raise ValueError
    except ValueError:
        await message.reply('Invalid value. Please provide a non-negative whole number.')
        return

    chat = await DataAccessLayer.get_chat(tg_id=message.chat.id)

    if chat is None:
        await message.reply('Bot was not started yet!')
        return

    updated = await DataAccessLayer.set_threshold(chat_id=chat.id, src=src, dst=dst, threshold=threshold)

    if not updated:
        await message.reply('Direction not found. Add it first with /add')
        return

    await message.reply(f'Threshold updated: {threshold} EUR')


dp.include_router(router)


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
