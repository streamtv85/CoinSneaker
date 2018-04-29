import logging
import configparser
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

from bot.events import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
config = configparser.ConfigParser()
config.read('config.ini')


def add_handlers(disp):
    start_handler = CommandHandler('start', start)
    disp.add_handler(start_handler)

    welcome_handler = MessageHandler(Filters.status_update.new_chat_members, welcome)
    disp.add_handler(welcome_handler)

    echo_handler = MessageHandler(Filters.text, echo, pass_user_data=True)
    disp.add_handler(echo_handler)

    caps_handler = CommandHandler('caps', caps, pass_args=True)
    disp.add_handler(caps_handler)

    # should be added as the LAST handler
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)


updater = Updater(token=config.get('MAIN', 'token'))

print("Checking if bot is okay")
print(updater.bot.get_me())
dispatcher = updater.dispatcher

add_handlers(dispatcher)

# polling loop
print("The bot has started.")
updater.start_polling()
