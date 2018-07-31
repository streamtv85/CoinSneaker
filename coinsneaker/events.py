import html
import os
import random
import re
from time import sleep

import arrow as arrow
import emoji
import requests
import telegram
from urllib.parse import urlencode
import logging

from coinsneaker import dbmanager, graph

logger = logging.getLogger('bot-service.events')


def send_graph(bot, update, args):
    debug_info(bot, update)
    reply = ""
    target_file = '{0}.png'.format(update.message.chat_id)
    period = 2
    if args:
        try:
            period = int(args[0])
        except ValueError:
            logger.warning("invalid argument was given. Using default period: {0}".format(period))
            reply = "Я, конечно, силен, но график на такое количество часов построить не в силах... Два часа - мой ответ"
    # if not (0 < period < 48):
    #     reply = "Я, конечно, силен, но график аж на {0} часов построить не в силах... Два часа - мой ответ".format(
    #         period)
    #     period = 2
    logger.debug("target file: " + target_file)
    if reply:
        update.message.reply_text(reply)
    event_info("Graph request for {0} hours".format(period), update, "target file: " + target_file)
    if not graph.generate_graph(target_file, period):
        update.message.reply_text("Произошла ошибка при построении графика. Не хватает входных данных?")
        return
    bot.send_photo(chat_id=update.message.chat_id, photo=open(target_file, 'rb'))
    os.remove(target_file)


def send_advanced_graph(bot, update, args):
    debug_info(bot, update)
    reply = ""
    target_file = '{0}_dbg.png'.format(update.message.chat_id)
    period = 2
    if args:
        try:
            period = int(args[0])
        except ValueError:
            logger.warning("invalid argument was given. Using default period: {0}".format(period))
            reply = "Я, конечно, силен, но график на такое количество часов построить не в силах... Два часа - мой ответ"
    # if not (0 < period < 12):
    #     reply = "Я, конечно, силен, но график аж на {0} часов построить не в силах... Два часа - мой ответ".format(
    #         period)
    #     period = 2
    logger.debug("target file: " + target_file)
    if reply:
        update.message.reply_text(reply)
    event_info("Advanced graph request for {0} hours".format(period), update, "target file: " + target_file)
    if not graph.generate_graph(target_file, period, debug=True):
        update.message.reply_text("Произошла ошибка при построении графика. Не хватает входных данных?")
        return
    bot.send_photo(chat_id=update.message.chat_id, photo=open(target_file, 'rb'))
    os.remove(target_file)


def start(bot, update):
    debug_info(bot, update)
    text = "I'm a bot, please talk to me!"
    event_info("START command", update, text)
    bot.send_message(chat_id=update.message.chat_id, text=text)


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
    event_info("Echo text", update, prefix + update.message.text)
    bot.send_message(chat_id=update.message.chat_id, text=prefix + update.message.text)


def el_bday(bot, update):
    debug_info(bot, update)
    now = arrow.now()
    if now.day == 28 and now.month == 7:
        event_info("What is the day today? Elya bday!", update, "")
        excl = emoji.emojize(":heart:",
                     use_aliases=True) + emoji.emojize(":birthday:",
                                       use_aliases=True) + emoji.emojize(":cocktail:",
                                                         use_aliases=True) + emoji.emojize(":gift:",
                                                                                     use_aliases=True)
        bot.send_message(chat_id=update.message.chat_id,
                         text="Сегодня? День рождения Эли! С ДНЕМ РОЖДЕНИЯ!!! " + excl)
    else:
        echo(bot, update)

def el(bot, update):
    debug_info(bot, update)
    event_info("Elya was mentioned!", update, "")
    bot.send_message(chat_id=update.message.chat_id,
                     text="Эля - милейшая девушка из всех, с которыми мы когда-либо общались, хоть иногда и врединка)")

def unknown(bot, update):
    debug_info(bot, update)
    reply = "Sorry, I didn't understand that command."
    event_info("Unknown command", update, reply)
    bot.send_message(chat_id=update.message.chat_id, text=reply)


def caps(bot, update, args):
    text_caps = ' '.join(args).upper()
    debug_info(bot, update)
    event_info("/caps command", update, text_caps)
    bot.send_message(chat_id=update.message.chat_id, text=text_caps)


def welcome(bot, update):
    debug_info(bot, update)
    message = "Добро пожаловать в наш чатик!"
    bot.send_message(chat_id=update.message.chat_id, text=message)


# It turned out that mentions are only possible in group chats. You cannot mention someone in private chat
def mention(bot, update):
    debug_info(bot, update)
    if i_was_mentioned(bot, update):
        reply = "Кто меня звал?"
        event_info("Mention", update, reply)
        update.message.reply_text(reply)


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


def joke(bot, update):
    sources = ['bash.im', 'anekdot.ru']
    url = "http://umorili.herokuapp.com/api/sources"
    source_number = random.randint(0, len(sources) - 1)
    reply = ""
    response = requests.get(url)
    if response.status_code == 200:
        matches = [x for x in response.json() if x[0]['site'] == sources[source_number]]
        if matches:
            site = matches[0][0]['site']
            name = matches[0][0]['name']
        encoded_args = urlencode({'site': site, 'name': name, 'num': 100})
        url = "http://umorili.herokuapp.com/api/get?" + encoded_args
        response = requests.get(url)
    if response.status_code != 200:
        logger.warning(
            "Status code was {0} when accessing {1}".format(response.status_code, url))
        reply = "Эм... Боюсь вам эта шутка не понравится..."
    else:
        number = random.randint(0, len(response.json()) - 1)
        reply = html.unescape(response.json()[number]['elementPureHtml'])
        reply = re.sub(r'<a.*/a>,*', '', str(reply))
        reply = re.sub(r'<[^<]+?>', '', str(reply))
        reply = re.sub(r'Проголосовать:', '', str(reply))
        logger.debug("joke text: from {0}: {1}".format(url, reply))
    event_info("Joke request", update, site + ":\n" + reply)
    bot.send_message(chat_id=update.message.chat_id, text=reply)


def history(bot, update, args):
    filenames = graph.get_exchange_data_files()
    number = 0
    if 'list' in args:
        s = "List of exchange history files (newest first):\n"
        for index, item in enumerate(filenames):
            s += "{0}: {1}\n".format(index, item)
        event_info("Show list of exchange data files", update, s)
        update.message.reply_text(s)
    else:
        if args:
            try:
                number = int(args[0])
            except ValueError:
                logger.warning("invalid argument was given. Using default: {0}".format(number))
                update.message.reply_text("Invalid index. Please specify integer number.")
                return
            if not (0 < number < len(filenames)):
                update.message.reply_text(
                    "Invalid index. Please specify from range: {0}..{1}".format(0, len(filenames) - 1))
                return
        event_info("Sending exchange data file {0!r}".format(filenames[number]), update, "")
        bot.send_document(chat_id=update.message.chat_id, document=open(filenames[number], 'rb'))


def debug_info(bot, update):
    logger.debug(' > received message from chat id: ' + str(update.message.chat_id))
    logger.debug(' > from user: ' + str(update.message.from_user))
    logger.debug(' > message text: ' + str(update.message.text))
    logger.debug(
        ' > chat member info: ' + str(bot.get_chat_member(update.message.chat_id, update.message.from_user.id)))


def event_info(prefix, update, message):
    if message:
        suffix = "Response:\n"
    else:
        suffix = ""
    logger.info(
        prefix + ": chat id {0!s}, user {1} ({2}). ".format(
            update.message.chat_id, update.message.from_user.username if update.message.from_user.username else (
                    update.message.from_user.first_name + update.message.from_user.last_name),
            update.message.from_user.id) + suffix + message)
