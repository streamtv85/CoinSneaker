import logging
import configparser
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

from bot.events import *

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


def add_message_handlers(disp):
    welcome_handler = MessageHandler(Filters.status_update.new_chat_members, welcome)
    disp.add_handler(welcome_handler)

    echo_handler = MessageHandler(Filters.text, echo)
    disp.add_handler(echo_handler)


def add_command_handlers(disp):
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


def callback_minute(bot, job):
    list_of_chats = get_all_chats()
    for chat in list_of_chats:
        bot.send_message(chat_id=chat[0], text='One message every minute')


# if get_all_chats():
#     print('getting the list of chat users')
#     for chat in get_all_chats():
#         print('chat id: ' + str(chat[0]))
#         print(updater.bot.get_chat(chat[0]).get_members_count())
#         print(updater.bot.get_chat(chat[0]).get_member())

# job_minute = job_queue.run_repeating(callback_minute, interval=60, first=0)

# polling loop
logger.info("The bot has started.")
updater.start_polling()
