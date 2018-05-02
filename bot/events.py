from bot.dbmanager import *
import logging

# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger('bot-service.events')


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


def subscribe(bot, update):
    chat_id = update.message.chat_id
    logger.info("subscribe: add chat id: " + str(chat_id))
    logger.debug("full list of subscribers: " + str(get_all_chats()))
    if chat_id not in get_all_chats():
        add_chat(chat_id)
        logger.info("added.")
        bot.send_message(chat_id=chat_id, text="Okay, you have been subscribed.")
    else:
        logger.info("was already there, nothing to add")
        bot.send_message(chat_id=chat_id, text="You were already subscribed, nothing to do")


def unsubscribe(bot, update):
    chat_id = update.message.chat_id
    logger.info("unsubscribe: remove chat id: " + str(chat_id))
    logger.debug("full list of subscribers: " + str(get_all_chats()))
    if chat_id in get_all_chats():
        delete_chat(chat_id)
        logger.info("deleted.")
        bot.send_message(chat_id=chat_id, text="No worries, you have been unsubscribed.")
    else:
        logger.info("wasn't there, nothing to delete")
        bot.send_message(chat_id=chat_id, text="You were not subscribed, so nothing to do")


def echo(bot, update):
    prefix = ""
    if update.message.text.startswith("ты"):
        prefix = "сам "
    print('received message from chat: %' + str(update.message.chat_id))
    print('received message from user: %' + str(update.message.from_user))
    print('user is: ' + str(bot.get_chat_member(update.message.chat_id, update.message.from_user.id)))
    bot.send_message(chat_id=update.message.chat_id, text=prefix + update.message.text)


def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def caps(bot, update, args):
    text_caps = ' '.join(args).upper()
    print('received message from chat: %' + str(update.message.chat_id))
    print('received message from user: %' + str(update.message.from_user))
    print('user is: ' + str(bot.get_chat_member(update.message.chat_id, update.message.from_user.id)))
    bot.send_message(chat_id=update.message.chat_id, text=text_caps)


def welcome(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Добро пожаловать в наш чатик!")
