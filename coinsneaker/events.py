import os
from time import sleep
import emoji

import telegram

from coinsneaker import dbmanager, graph

import logging

logger = logging.getLogger('bot-service.events')


def send_graph(bot, update, args):
    debug_info(bot, update)

    target_file = '{0}.png'.format(update.message.chat_id)
    period = 2
    if args:
        try:
            period = int(args[0])
        except ValueError:
            logger.warning("invalid argument was given. Using default period: {0}".format(period))
    logger.info(
        "Request to plot graph for {0} minutes from chat id {1}, user {2}".format(period, update.message.chat_id,
                                                                                    update.message.from_user.username))
    graph.generate_graph(target_file, period)
    bot.send_photo(chat_id=update.message.chat_id, photo=open(target_file, 'rb'))
    os.remove(target_file)


def start(bot, update):
    debug_info(bot, update)
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


def subscribe(bot, update):
    chat_id = update.message.chat_id
    logger.info("subscribe: add chat id: " + str(chat_id))
    logger.debug("full list of subscribers: " + str(dbmanager.get_all_chats()))
    if chat_id not in dbmanager.get_all_chats():
        dbmanager.add_chat(chat_id)
        logger.info("added.")
        bot.send_message(chat_id=chat_id, text="Okay, you have been subscribed.")
    else:
        logger.info("was already there, nothing to add")
        bot.send_message(chat_id=chat_id, text="You were already subscribed, nothing to do")


def unsubscribe(bot, update):
    chat_id = update.message.chat_id
    logger.info("unsubscribe: remove chat id: " + str(chat_id))
    logger.debug("full list of subscribers: " + str(dbmanager.get_all_chats()))
    if chat_id in dbmanager.get_all_chats():
        dbmanager.delete_chat(chat_id)
        logger.info("deleted.")
        bot.send_message(chat_id=chat_id, text="No worries, you have been unsubscribed.")
    else:
        logger.info("wasn't there, nothing to delete")
        bot.send_message(chat_id=chat_id, text="You were not subscribed, so nothing to do")


def echo(bot, update):
    prefix = ""
    if update.message.text.startswith("ты"):
        prefix = "сам "
    debug_info(bot, update)
    bot.send_message(chat_id=update.message.chat_id, text=prefix + update.message.text)


def el(bot, update):
    debug_info(bot, update)
    bot.send_message(chat_id=update.message.chat_id, text="А Эля милашка, ты знаешь?")


def unknown(bot, update):
    debug_info(bot, update)
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def caps(bot, update, args):
    text_caps = ' '.join(args).upper()
    debug_info(bot, update)
    bot.send_message(chat_id=update.message.chat_id, text=text_caps)


def welcome(bot, update):
    debug_info(bot, update)
    bot.send_message(chat_id=update.message.chat_id, text="Добро пожаловать в наш чатик!")


# It turned out that mentions are only possible in group chats. You cannot mention someone in private chat
def mention(bot, update):
    debug_info(bot, update)
    if i_was_mentioned(bot, update):
        update.message.reply_text("Кто меня звал?")


def i_was_mentioned(bot, update):
    mentions = update.message.parse_entities(telegram.MessageEntity.MENTION)
    logger.debug("all mentions: " + str(mentions.values()))
    return ('@' + bot.get_me()['username']) in mentions.values()


def master(bot, update):
    debug_info(bot, update)
    bot.send_message(chat_id=update.message.chat_id,
                     text="Моя Хазяина" + emoji.emojize(":heart_eyes:", use_aliases=True))
    sleep(3)
    bot.send_photo(chat_id=update.message.chat_id, photo=open('tests/test.png', 'rb'))


def debug_info(bot, update):
    logger.debug(' > received message from chat id: ' + str(update.message.chat_id))
    logger.debug(' > from user: ' + str(update.message.from_user))
    logger.debug(' > message text: ' + str(update.message.text))
    logger.debug(
        ' > chat member info: ' + str(bot.get_chat_member(update.message.chat_id, update.message.from_user.id)))
