#!/usr/bin/env python3

import glob
from logging.handlers import TimedRotatingFileHandler

import os
from shutil import make_archive

from telegram import MessageEntity  # fades.pypi python-telegram-bot
from telegram.ext import Updater  # fades.pypi python-telegram-bot
from telegram.ext import CommandHandler  # fades.pypi python-telegram-bot
from telegram.ext import MessageHandler, Filters  # fades.pypi python-telegram-bot

from coinsneaker.events import *  # fades.pypi
from coinsneaker.exchange import *  # fades.pypi
from coinsneaker.configmanager import config  # fades.pypi

cwd = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger('bot-service')
log_level = config.get('logLevel')
logger.setLevel(logging.getLevelName(log_level))
# create file handler which logs even debug messages
logfilename = os.path.join(cwd, 'bot-service.log')
fh = TimedRotatingFileHandler(logfilename, when='D', interval=1, backupCount=config.get('logMaxAge'),
                              encoding='utf_8')
fh.setLevel(logging.getLevelName(log_level))
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.getLevelName(log_level))
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

price_diff_ma_slow = 0.0
price_diff_ma_fast = 0.0
price_diff = 0.0
price_diff_prev = 0.0
price_ma_period_slow = 20
price_ma_period_fast = 3
price_avg_ma_fast = 0.0
price_exmo = 0.0
price_bitfin = 0.0

alert = False


def send_prices(bot, update):
    percent = round(price_diff_ma_fast / price_avg_ma_fast * 100, 3)
    message = "Цены BTC/USD: Exmo {0}, Bitfinex {1}, разница цен: {2} USD ({3}%)".format(
        price_exmo,
        price_bitfin,
        round(price_diff_ma_fast, 2),
        percent)
    logger.info(
        "Price request received: chat id {0}, from user {1} (id: {2}). Sending text: {3}".format(str(
            update.message.chat_id), update.message.from_user.username,
            update.message.from_user.id, message))
    bot.send_message(chat_id=update.message.chat_id, text=message)


def add_message_handlers(disp):
    logger.info("Adding message handlers.")
    welcome_handler = MessageHandler(Filters.status_update.new_chat_members, welcome)
    disp.add_handler(welcome_handler)

    mention_handler = MessageHandler(Filters.entity(MessageEntity.MENTION), mention)
    disp.add_handler(mention_handler)

    el_handler = MessageHandler(Filters.regex(r"\s*Эля\s*"), el)
    disp.add_handler(el_handler)

    echo_handler = MessageHandler(Filters.text, echo)
    disp.add_handler(echo_handler)


def add_command_handlers(disp):
    logger.info("Adding command handlers.")
    start_handler = CommandHandler('start', start)
    disp.add_handler(start_handler)

    sub_handler = CommandHandler('subscribe', subscribe)
    disp.add_handler(sub_handler)

    unsub_handler = CommandHandler('unsubscribe', unsubscribe)
    disp.add_handler(unsub_handler)

    prices_handler = CommandHandler('price', send_prices)
    disp.add_handler(prices_handler)

    caps_handler = CommandHandler('caps', caps, pass_args=True)
    disp.add_handler(caps_handler)

    # should be added as the LAST handler
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)


def get_exchange_data():
    global price_diff_prev, price_diff_ma_slow, price_diff_ma_fast, price_avg_ma_fast, alert, price_exmo, price_bitfin

    price_diff_prev = price_diff_ma_fast
    price_exmo = get_exmo_btc_price()
    price_bitfin = get_bitfinex_btc_price()
    price_diff = round(price_bitfin - price_exmo, 2)
    # price_diff = get_price_diff_mock()
    price_avg = round((price_exmo + price_bitfin) / 2, 2)

    price_diff_ma_slow = update_ma(price_diff, price_diff_ma_slow, price_ma_period_slow)
    price_diff_ma_fast = update_ma(price_diff, price_diff_ma_fast, price_ma_period_fast)
    price_avg_ma_fast = update_ma(price_avg, price_avg_ma_fast, price_ma_period_fast)

    logger.debug(
        "Bitfinex - Exmo price difference is {0} USD, before it was {1} USD. Slow MA: {2}, Fast MA: {3}".format(
            price_diff,
            price_diff_prev,
            round(price_diff_ma_slow, 2),
            round(price_diff_ma_fast, 2)))

    if price_diff_prev == 0.0:
        price_diff_prev = price_diff_ma_fast
    # logger.info("price diff: " + str(price_diff))
    return price_diff


def callback_exchanges_data(bot, job):
    global alert, price_diff
    price_diff = get_exchange_data()

    percent = round(price_diff_ma_fast / price_avg_ma_fast * 100, 3)
    # if price_diff * price_diff_prev < 0:
    # price difference changed sign
    # text = "Warning! Exmo - Bitfinex price difference has changed. Now it equals {0}, before it was {1}".format(
    #     price_diff, price_diff_prev)

    logger.debug(
        "Avg price: {0}, Exmo price: {1}, Bitfinex price: {2}, diff: {3}%, abs(diff): {4}%".format(
            round(price_avg_ma_fast, 2),
            price_exmo,
            price_bitfin,
            percent, math.fabs(percent)))

    if price_diff_ma_fast * price_diff_prev < 0:
        excl = emoji.emojize(":bangbang:", use_aliases=True)
        text = excl + "Внимание, Сменила знак разница цен BTC/USD между Bitfinex и Exmo. Было {0}, стало {1} USD".format(
            round(price_diff_prev, 2), round(price_diff_ma_fast, 2))
        send_text_to_subscribers(bot, text)
        logger.info("Alert is now True. Alert messages sent! Text: {0}".format(text))
        alert = True
    else:
        if (math.fabs(percent) <= 0.2) or (1 < percent < 3.0) or (1.8 < -percent < 3.0):
            excl = emoji.emojize(":exclamation:", use_aliases=True)
            if not alert:
                text = excl + "Внимание" + excl + " Разница цен BTC/USD между Bitfinex и Exmo достигла {0}%, а именно {1} USD".format(
                    percent, round(price_diff_ma_fast, 2))
                send_text_to_subscribers(bot, text)
                logger.info("Alert is now True. Alert messages sent! Text: {0}".format(text))
                alert = True
        else:
            logger.debug("Alert is now False. Looking for new triggers.")
            alert = False

    # write values to exchange history file
    header_text = "Timestamp,Exmo price,Bitfinex price,price diff, diff MA{0}, diff MA{1},diff percent,alert\n".format(
        price_ma_period_fast, price_ma_period_slow)
    csv = "{0},{1},{2},{3},{4},{5},{6},{7}\n".format(
        time.strftime("%c"),
        price_exmo,
        price_bitfin,
        round(price_diff, 2),
        round(price_diff_ma_fast, 2),
        round(price_diff_ma_slow, 2),
        percent,
        alert)
    write_exchange_data_to_file(header_text, csv)


def send_text_to_subscribers(bot, text):
    list_of_chats = get_all_chats()
    logger.debug('List of chats to send message to: ' + str(list_of_chats))
    for chat in list_of_chats:
        bot.send_message(chat_id=chat, text=text)


def write_exchange_data_to_file(header, text):
    folder = config.get('csvFolder')
    csv_prefix = config.get('csvPrefix')
    logger.debug("Creating folder: " + folder)
    os.makedirs(folder, exist_ok=True)
    data_filename = time.strftime(csv_prefix + "-%d-%m-%Y")
    csv_ext = '.csv'
    full_path = path.join(cwd, folder, data_filename + csv_ext)
    exists = path.exists(full_path)
    f = open(full_path, "a+")
    if not exists:
        logger.info("file '" + full_path + "' does not exist. Writing header")
        f.write(header)
    logger.debug("filename with exchange data: " + data_filename)
    f.write(text)
    f.close()
    archive_old_files(path.join(cwd, folder, "exchange-data*.csv"))


def archive_old_files(pattern):
    current_time = time.time()
    for f in glob.glob(pattern):
        if os.path.isfile(f):
            creation_time = os.path.getctime(f)
            (name, ext) = os.path.splitext(f)
            # archive file if older than 7 days
            if (current_time - creation_time) // (24 * 3600) >= float(config.get('exchangeDataAge')):
                logger.info("File {0} is older than 7 days. Zip it!")
                make_archive(name, 'zip', '.', f)
                os.remove(f)


# if get_all_chats():
#     print('getting the list of chat users')
#     for chat in get_all_chats():
#         print('chat id: ' + str(chat[0]))
#         print(updater.bot.get_chat(chat[0]).get_members_count())
#         print(updater.bot.get_chat(chat[0]).get_member())


if __name__ == "__main__":
    logger.info("Current folder is: " + cwd)
    updater = Updater(token=config.get('token'))
    job_queue = updater.job_queue

    logger.info("Checking if bot is okay")
    logger.info(updater.bot.get_me())

    dispatcher = updater.dispatcher
    add_message_handlers(dispatcher)
    add_command_handlers(dispatcher)
    logger.info("init regular job for execution")
    job_minute = job_queue.run_repeating(callback_exchanges_data, interval=60, first=0)

    # polling loop
    logger.info("The bot has started.")
    updater.start_polling()
