def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


def echo(bot, update):
    prefix = ""

    if update.message.text.startswith("ты"):
        prefix = "сам "
    bot.send_message(chat_id=update.message.chat_id, text=prefix + update.message.text)


def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")


def caps(bot, update, args):
    text_caps = ' '.join(args).upper()
    bot.send_message(chat_id=update.message.chat_id, text=text_caps)


def welcome(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Добро пожаловать в наш чатик!")
