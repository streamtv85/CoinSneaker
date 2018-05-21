import glob
import logging
from logging.handlers import TimedRotatingFileHandler

import configparser
import os
from os import path
from shutil import make_archive

from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

from bot.events import *
from bot.exchange_ticker import *

config = configparser.ConfigParser()
config.read('config.ini')

logger = logging.getLogger('bot-service')
logger.setLevel(logging.getLevelName(config.get('MAIN', 'logLevel')))
# create file handler which logs even debug messages
fh = TimedRotatingFileHandler('bot-service.log', when='D', interval=1, backupCount=config.get('MAIN', 'logMaxAge'),
                              encoding='utf_8')
fh.setLevel(logging.getLevelName(config.get('MAIN', 'logLevel')))
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.getLevelName(config.get('MAIN', 'logLevel')))
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

price_diff_ma_slow = 0.0
price_diff_ma_fast = 0.0
price_diff_prev = 0.0
price_ma_period_slow = 20
price_ma_period_fast = 3
price_avg_ma_fast = 0.0
price_exmo = 0.0
price_bitfin = 0.0

alert = False


def add_message_handlers(disp):
    logger.info("adding message handlers")
    welcome_handler = MessageHandler(Filters.status_update.new_chat_members, welcome)
    disp.add_handler(welcome_handler)

    el_handler = MessageHandler(Filters.regex(r"\s*Эля\s*"), el)
    disp.add_handler(el_handler)

    echo_handler = MessageHandler(Filters.text, echo)
    disp.add_handler(echo_handler)


def add_command_handlers(disp):
    logger.info("adding command handlers")
    start_handler = CommandHandler('start', start)
    disp.add_handler(start_handler)

    sub_handler = CommandHandler('subscribe', subscribe)
    disp.add_handler(sub_handler)

    unsub_handler = CommandHandler('unsubscribe', unsubscribe)
    disp.add_handler(unsub_handler)

    caps_handler = CommandHandler('caps', caps, pass_args=True)
    disp.add_handler(caps_handler)

    # should be added as the LAST handler
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)


updater = Updater(token=config.get('MAIN', 'token'))
job_queue = updater.job_queue

logger.info("Checking if bot is okay")
logger.info(updater.bot.get_me())

dispatcher = updater.dispatcher
add_message_handlers(dispatcher)
add_command_handlers(dispatcher)


def get_exchange_data():
    global price_diff_prev, price_diff_ma_slow, price_diff_ma_fast, price_avg_ma_fast, alert, price_exmo, price_bitfin
    # price_diff = get_price_diff()
    price_diff = get_price_diff(mock=True)
    price_exmo = get_exmo_btc_price()
    price_bitfin = get_bitfinex_btc_price()
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

    price_diff_prev = price_diff
    return price_diff


def callback_exchanges_data(bot, job):
    global alert
    price_diff = get_exchange_data()

    percent = round(price_diff_ma_fast / price_avg_ma_fast * 100, 4)
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

    if (math.fabs(percent) <= 0.2) or (1.8 < math.fabs(percent) < 3.0):
        excl = emoji.emojize(":exclamation:", use_aliases=True)
        if not alert:
            text = excl + "Внимание" + excl + " Разница цен BTC/USD между Exmo и Bitfinex достигла {0}%".format(
                percent)
            send_text_to_subscribers(bot, text)
            logger.info("Alert is now True. Alert messages sent!Text: {0}".format(text))
            alert = True
    else:
        logger.debug("Alert is now False. Looking for new triggers.")
        alert = False

    # write values to exchange history file
    header_text = "Timestamp,Exmo price,Bitfinex price,price diff, diff MA{0}, diff MA{1},diff percent,alert\n".format(
        price_ma_period_fast, price_ma_period_slow)
    csv = "{0},{1},{2},{3},{5},{6},{7}\n".format(
        time.strftime("%c"),
        price_exmo,
        price_bitfin,
        price_diff,
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
    data_filename = time.strftime("exchange-data-%d-%m-%Y")
    csv_ext = '.csv'
    exists = path.exists(data_filename + csv_ext)
    f = open(data_filename + csv_ext, "a+")
    if not exists:
        logger.info("file '" + data_filename + csv_ext + "' does not exist. Writing header")
        f.write(header)
    logger.debug("filename with exchange data: " + data_filename)
    f.write(text)
    f.close()
    archive_old_files("exchange-data*.csv")


def archive_old_files(pattern):
    current_time = time.time()
    for f in glob.glob(pattern):
        if os.path.isfile(f):
            creation_time = os.path.getctime(f)
            (name, ext) = os.path.splitext(f)
            # archive file if older than 7 days
            if (current_time - creation_time) // (24 * 3600) >= float(config.get('MAIN', 'exchangeDataAge')):
                logger.info("File {0} is older than 7 days. Zip it!")
                make_archive(name, 'zip', '.', f)
                os.remove(f)


# if get_all_chats():
#     print('getting the list of chat users')
#     for chat in get_all_chats():
#         print('chat id: ' + str(chat[0]))
#         print(updater.bot.get_chat(chat[0]).get_members_count())
#         print(updater.bot.get_chat(chat[0]).get_member())

logger.info("init regular job for execution")
job_minute = job_queue.run_repeating(callback_exchanges_data, interval=60, first=0)

# polling loop
logger.info("The bot has started.")
updater.start_polling()
