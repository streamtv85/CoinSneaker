from bot.dbmanager import *


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


def subscribe(bot, update):
    chat_id = update.message.chat_id
    if chat_id not in get_all_chats():
        add_chat(chat_id,'')
        bot.send_message(chat_id=chat_id, text="Okay, you have been subscribed.")
    else:
        bot.send_message(chat_id=chat_id, text="You were already subscribed, nothing to do")


def unsubscribe(bot, update):
    chat_id = update.message.chat_id
    if chat_id in get_all_chats():
        delete_chat(chat_id)
        bot.send_message(chat_id=chat_id, text="No worries, you have been unsubscribed.")
    else:
        bot.send_message(chat_id=chat_id, text="You were not subscribed, so nothing to do")


def echo(bot, update):
    prefix = ""
    if update.message.text.startswith("ты"):
        prefix = "сам "
    print(update.message.chat_id)
    bot.send_message(chat_id=update.message.chat_id, text=prefix + update.message.text)


def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def caps(bot, update, args):
    text_caps = ' '.join(args).upper()
    bot.send_message(chat_id=update.message.chat_id, text=text_caps)


def welcome(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Добро пожаловать в наш чатик!")
