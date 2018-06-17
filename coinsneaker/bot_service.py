#!/usr/bin/env python3

import glob
import logging
import math
import os
import sys
import time
from logging.handlers import TimedRotatingFileHandler
from shutil import make_archive
from threading import Thread

import emoji
from telegram import MessageEntity
from telegram.ext import MessageHandler, Filters, Updater, CommandHandler
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)

from coinsneaker import events, dbmanager, exchange, ExchangeWatcher, BitfinexBookWatcher
from coinsneaker.configmanager import config

cwd = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger('bot-service')
log_level = config.get('logLevel')
logger.setLevel(logging.getLevelName(log_level))
# create file handler which logs even debug messages
logfilename = os.path.join(cwd, 'bot-service.log')
fh = TimedRotatingFileHandler(logfilename, when='D', interval=1, backupCount=int(config.get('logMaxAge')),
                              encoding='utf_8')
fh.setLevel(logging.getLevelName(log_level))
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.getLevelName(log_level))
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

price_diff_ma_slow = 0.0
price_diff_ma_fast = 0.0
price_diff = 0.0
price_diff_prev = 0.0
price_ma_period_slow = 20
price_ma_period_fast = 3
price_avg_ma_fast = 0.0
price_exmo = 0.0
price_bitfin = 0.0

exmo_watcher = ExchangeWatcher('exmo', 'BTC/USD')
bitfin_watcher = ExchangeWatcher('bitfinex', 'BTC/USD')
data = exchange.DataHistoryManager(bitfin_watcher, exmo_watcher)
btf = BitfinexBookWatcher()

alert = False


def send_prices(bot, update):
    percent = round(price_diff_ma_fast / price_avg_ma_fast * 100, 3)
    message = "Цены BTC/USD: Exmo {0}, Bitfinex {1}, разница цен: {2} USD ({3}%)".format(
        price_exmo,
        price_bitfin,
        round(price_diff_ma_fast, 2),
        percent)
    logger.info(
        "Price request: chat id {0}, from {1} ({2}). Sending text: {3}".format(str(
            update.message.chat_id), update.message.from_user.username,
            update.message.from_user.id, message))
    bot.send_message(chat_id=update.message.chat_id, text=message)


def send_orderbook(bot, update):
    bid_total = btf.bid_depth
    bids = sorted(btf.bids.keys())
    # bids_price_range = abs(round(bids[0] - bids[-1]))
    ask_total = btf.ask_depth
    asks = sorted(btf.asks.keys())
    # asks_price_range = abs(round(asks[0] - asks[-1]))
    message = "BTC/USD стаканы Bitfinex:\nПокупка {0} BTC (в диапазоне {1}..{2} USD)\nПродажа {3} BTC (в диапазоне {4}..{5} USD)".format(
        round(bid_total, 2),
        bids[0],
        bids[-1],
        round(ask_total, 2),
        asks[0],
        asks[-1]
    )
    logger.info(
        "Orderbook request: chat id {0}, from {1} ({2}). Sending text: {3}".format(str(
            update.message.chat_id), update.message.from_user.username,
            update.message.from_user.id, message))
    bot.send_message(chat_id=update.message.chat_id, text=message)


def add_message_handlers(disp):
    logger.info("Adding message handlers.")
    welcome_handler = MessageHandler(Filters.status_update.new_chat_members, events.welcome)
    disp.add_handler(welcome_handler)

    mention_handler = MessageHandler(Filters.entity(MessageEntity.MENTION), events.mention)
    disp.add_handler(mention_handler)

    el_handler = MessageHandler(Filters.regex(r"\s*Эля\s*"), events.el)
    disp.add_handler(el_handler)

    echo_handler = MessageHandler(Filters.text, events.echo)
    disp.add_handler(echo_handler)


def add_command_handlers(disp):
    logger.info("Adding command handlers.")
    start_handler = CommandHandler('start', events.start)
    disp.add_handler(start_handler)

    sub_handler = CommandHandler('subscribe', events.subscribe)
    disp.add_handler(sub_handler)

    unsub_handler = CommandHandler('unsubscribe', events.unsubscribe)
    disp.add_handler(unsub_handler)

    prices_handler = CommandHandler('price', send_prices)
    disp.add_handler(prices_handler)

    caps_handler = CommandHandler('caps', events.caps, pass_args=True)
    disp.add_handler(caps_handler)

    graph_handler = CommandHandler('graph', events.send_graph, pass_args=True)
    disp.add_handler(graph_handler)

    history_handler = CommandHandler('history', events.history, pass_args=True)
    disp.add_handler(history_handler)

    joke_handler = CommandHandler('joke', events.joke)
    disp.add_handler(joke_handler)

    ob_handler = CommandHandler('orderbook', send_orderbook)
    disp.add_handler(ob_handler)

    # should be added as the LAST handler
    unknown_handler = MessageHandler(Filters.command, events.unknown)
    disp.add_handler(unknown_handler)


def get_exchange_data():
    global price_diff_prev, price_diff_ma_slow, price_diff_ma_fast, price_avg_ma_fast, alert, price_exmo, price_bitfin

    price_diff_prev = price_diff_ma_fast
    price_exmo = exchange.get_exmo_btc_price()
    price_bitfin = exchange.get_bitfinex_btc_price()
    price_diff = round(price_bitfin - price_exmo, 2)
    # price_diff = get_price_diff_mock()
    price_avg = round((price_exmo + price_bitfin) / 2, 2)

    price_diff_ma_slow = exchange.update_ma(price_diff, price_diff_ma_slow, price_ma_period_slow)
    price_diff_ma_fast = exchange.update_ma(price_diff, price_diff_ma_fast, price_ma_period_fast)
    price_avg_ma_fast = exchange.update_ma(price_avg, price_avg_ma_fast, price_ma_period_fast)

    logger.debug(
        "Bitfinex - Exmo price difference is {0} USD, before it was {1} USD. Slow MA: {2}, Fast MA: {3}".format(
            price_diff,
            price_diff_prev,
            round(price_diff_ma_slow, 2),
            round(price_diff_ma_fast, 2)))

    if price_diff_prev == 0.0:
        price_diff_prev = price_diff_ma_fast
    # logger.info("price diff: " + str(price_diff))
    return price_diff


def callback_orderbook_updates(bot, job):
    btf.get_updates()


def callback_exchanges_data(bot, job):
    global alert, price_diff, data
    data.update()
    price_diff = get_exchange_data()

    percent = round(price_diff_ma_fast / price_avg_ma_fast * 100, 3)

    logger.debug(
        "Avg price: {0}, Exmo price: {1}, Bitfinex price: {2}, diff: {3}%, abs(diff): {4}%".format(
            round(price_avg_ma_fast, 2),
            price_exmo,
            price_bitfin,
            percent, math.fabs(percent)))

    if price_diff_ma_fast * price_diff_prev < 0:
        excl = emoji.emojize(":bangbang:", use_aliases=True)
        text = excl + "Внимание, Сменила знак разница цен BTC/USD между Bitfinex и Exmo. Было {0}, стало {1} USD".format(
            round(price_diff_prev, 2), round(price_diff_ma_fast, 2))
        send_text_to_subscribers(bot, text)
        logger.info("Alert is now True. Alert messages sent! Text: {0}".format(text))
        alert = True
    else:
        if (math.fabs(percent) <= 0.2) or (1 < percent < 3.0) or (1.8 < -percent < 3.0) or (0.5 < percent < 0.65):
            excl = emoji.emojize(":exclamation:", use_aliases=True)
            if not alert:
                text = excl + "Внимание" + excl + " Разница цен BTC/USD между Bitfinex и Exmo достигла {0}%, а именно {1} USD".format(
                    percent, round(price_diff_ma_fast, 2))
                send_text_to_subscribers(bot, text)
                logger.info("Alert is now True. Alert messages sent! Text: {0}".format(text))
                alert = True
        else:
            logger.debug("Alert is now False. Looking for new triggers.")
            alert = False

    # write values to exchange history file
    header_text = "Timestamp,Exmo price,Bitfinex price,price diff, diff MA{0}, diff MA{1},diff percent,alert\n".format(
        price_ma_period_fast, price_ma_period_slow)
    csv = "{0},{1},{2},{3},{4},{5},{6},{7}\n".format(
        time.strftime("%c"),
        price_exmo,
        price_bitfin,
        round(price_diff, 2),
        round(price_diff_ma_fast, 2),
        round(price_diff_ma_slow, 2),
        percent,
        alert)
    write_exchange_data_to_file(header_text, csv)


def send_text_to_subscribers(bot, text):
    list_of_chats = dbmanager.get_all_chats()
    logger.debug('List of chats to send message to: ' + str(list_of_chats))
    for chat in list_of_chats:
        bot.send_message(chat_id=chat, text=text)


def write_exchange_data_to_file(header, text):
    folder = config.get('csvFolder')
    csv_prefix = config.get('csvPrefix')
    logger.debug("Creating folder: " + folder)
    os.makedirs(folder, exist_ok=True)
    data_filename = time.strftime(csv_prefix + "-%d-%m-%Y")
    csv_ext = '.csv'
    full_path = os.path.join(cwd, folder, data_filename + csv_ext)
    exists = os.path.exists(full_path)
    f = open(full_path, "a+")
    if not exists:
        logger.info("file '" + full_path + "' does not exist. Writing header")
        f.write(header)
    logger.debug("filename with exchange data: " + data_filename)
    f.write(text)
    f.close()
    archive_old_files(os.path.join(cwd, folder, csv_prefix + "*.csv"))


def archive_old_files(pattern):
    current_time = time.time()
    for f in glob.glob(pattern):
        if os.path.isfile(f):
            creation_time = os.path.getctime(f)
            (name, ext) = os.path.splitext(f)
            # archive file if older than 7 days
            if (current_time - creation_time) // (24 * 3600) >= float(config.get('exchangeDataAge')):
                logger.info("File {0} is older than 7 days. Zip it!".format(str(f)))
                make_archive(name, 'zip', '.', f)
                os.remove(f)


def error_callback(bot, update, error):
    # for the future - if we need to handle any specific Telegram exceptions
    try:
        raise error
    except Unauthorized:
        pass
        # remove update.message.chat_id from conversation list
    except BadRequest:
        pass
    # handle malformed requests - read more below!
    except TimedOut:
        pass
    # handle slow connection problems
    except NetworkError:
        pass
    # handle other connection problems
    except ChatMigrated as e:
        pass
    # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        pass
    # handle all other telegram related errors


# main entry point, executed when the file is being run as a script
def main():
    logger.info("Current folder is: " + cwd)
    updater = Updater(token=config.get('token'))
    job_queue = updater.job_queue
    logger.info("Checking if bot is okay")
    logger.info(updater.bot.get_me())
    chats = dbmanager.get_all_chats()
    if chats:
        logger.info('List of subscribers:')
        logger.info(str(chats))
    dispatcher = updater.dispatcher
    logger.info("Starting Bitfinex websocket client")
    btf.start()

    def stop_and_restart():
        """Gracefully stop the Updater and replace the current process with a new one"""
        updater.stop()
        btf.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def restart(bot, update):
        logger.warning("Received restart command via Telegram")
        update.message.reply_text('Bot is restarting...')
        logger.debug("writing chat ID {0} to {1}".format(update.message.chat_id, master_file))
        with open(master_file, 'w') as f:
            f.write(str(update.message.chat_id))
        logger.debug("Restarting the thread")
        Thread(target=stop_and_restart).start()

    # Linux only
    def update(bot, update):
        logger.warning("Received Update command via Telegram")
        path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.abspath(os.path.join(path, "..", "update.sh"))
        if os.path.exists(full_path):
            logger.debug("sending notification message")
            update.message.reply_text('Triggering bot update process... See you later!')
            logger.debug("writing chat ID {0} to {1}".format(update.message.chat_id, master_file))
            with open(master_file, 'w') as f:
                f.write(str(update.message.chat_id))
            logger.debug("Stopping Bitfinex WebSocket client")
            btf.stop()
            logger.debug("Executing the script")
            os.system("nohup " + full_path + " &")
        else:
            logger.error("Update script was not found!")
            update.message.reply_text("Sorry haven't found and update script. Please do the update manually.")

    # dispatcher.add_error_handler(error_callback)
    dispatcher.add_handler(CommandHandler('restart', restart, filters=Filters.user(username='@streamtv85')))
    dispatcher.add_handler(CommandHandler('update', update, filters=Filters.user(username='@streamtv85')))

    add_command_handlers(dispatcher)
    add_message_handlers(dispatcher)
    logger.debug("List of registered handlers:")
    for current in list(dispatcher.handlers.values())[0]:
        logger.debug(str(current.callback.__name__))
    logger.info("init regular job to gather exchange data every minute")
    job_minute = job_queue.run_repeating(callback_exchanges_data, interval=60, first=0)
    logger.info("init regular job to get Bitfinex orderbook every second")
    job_orderbook_second = job_queue.run_repeating(callback_orderbook_updates, interval=1, first=0)
    logger.info("The bot has started.")
    updater.start_polling()
    master_file = "/tmp/master.txt"
    if os.path.exists(master_file):
        with open(master_file, 'r') as f:
            text = f.read()
        logger.debug("read chat id from " + master_file + " file: " + text)
        updater.bot.send_message(int(text), "I'm back bitches!")
        os.remove(master_file)
    logger.info("The bot is idle.")
    updater.idle()


if __name__ == "__main__":
    main()
