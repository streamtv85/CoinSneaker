import logging
import configparser
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

from bot.events import *

# import db.dbmanager

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
config = configparser.ConfigParser()
config.read('config.ini')


def add_handlers(disp):
    start_handler = CommandHandler('start', start)
    disp.add_handler(start_handler)

    sub_handler = CommandHandler('subscribe', subscribe)
    disp.add_handler(sub_handler)

    unsub_handler = CommandHandler('unsubscribe', unsubscribe)
    disp.add_handler(unsub_handler)

    welcome_handler = MessageHandler(Filters.status_update.new_chat_members, welcome)
    disp.add_handler(welcome_handler)

    echo_handler = MessageHandler(Filters.text, echo)
    disp.add_handler(echo_handler)

    caps_handler = CommandHandler('caps', caps, pass_args=True)
    disp.add_handler(caps_handler)

    # should be added as the LAST handler
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)


updater = Updater(token=config.get('MAIN', 'token'))
job_queue = updater.job_queue

print("Checking if bot is okay")
print(updater.bot.get_me())

dispatcher = updater.dispatcher
add_handlers(dispatcher)


def callback_minute(bot, job):
    list_of_chats = get_all_chats()
    for chat in list_of_chats:
        bot.send_message(chat_id=chat[0], text='One message every minute')


job_minute = job_queue.run_repeating(callback_minute, interval=60, first=0)

# polling loop
print("The bot has started.")
updater.start_polling()
