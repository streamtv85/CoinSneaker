import logging
import configparser
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

from bot.events import *
from bot.exchange_ticker import *

# create logger with 'spam_application'
logger = logging.getLogger('bot-service')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
# fh = logging.FileHandler('bot-service.log')
# fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
# logger.addHandler(fh)
logger.addHandler(ch)

# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
config = configparser.ConfigParser()
config.read('config.ini')

price_diff_ma = 0.0
price_diff_prev = 0.0
price_ma_period = 60


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


def callback_exchanges_data(bot, job):
    global price_diff_prev, price_diff_ma
    text = ""
    price_diff = round(get_bitfinex_btc_price() - get_exmo_btc_price(), 2)
    # if price_diff * price_diff_prev < 0:
    # price difference changed sign
    # text = "Warning! Exmo - Bitfinex price difference has changed. Now it equals {0}, before it was {1}".format(
    #     price_diff, price_diff_prev)

    text = "Bitfinex - Exmo price difference is {0} USD, before it was {1} USD. Average: {2}".format(price_diff,
                                                                                                     price_diff_prev,
                                                                                                     price_diff_ma)
    list_of_chats = get_all_chats()
    for chat in list_of_chats:
        bot.send_message(chat_id=chat, text=text)

    price_diff_prev = price_diff
    if price_diff_ma == 0:
        price_diff_ma = price_diff_prev
    price_diff_ma = (price_diff + price_ma_period * price_diff_ma) / (price_ma_period + 1)


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
