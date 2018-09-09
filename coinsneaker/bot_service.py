#!/usr/bin/env python3

import glob
import logging
import math
import os
import sys
import time
import emoji
from logging.handlers import TimedRotatingFileHandler
from shutil import make_archive
from threading import Thread
from telegram import MessageEntity, ParseMode, ChatAction
from telegram.ext import MessageHandler, Filters, Updater, CommandHandler
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)

from coinsneaker import events, dbmanager, exchange, graph, ExchangeWatcher, BitfinexBookWatcher, DataHistoryManager, \
    FundingWatcher
from coinsneaker.configmanager import config

cwd = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger('bot-service')
log_level = config.get('logLevel')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
logfilename = os.path.join(cwd, 'bot-service.log')
logdebugfilename = os.path.join(cwd, 'bot-service-debug.log')
fh = TimedRotatingFileHandler(logfilename, when='D', interval=1, backupCount=int(config.get('logMaxAge')),
                              encoding='utf_8')
fh.setLevel(logging.getLevelName(log_level))
fhdebug = TimedRotatingFileHandler(logdebugfilename, when='D', interval=1, backupCount=3, encoding='utf_8')
fhdebug.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.getLevelName(log_level))
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
fhdebug.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(fhdebug)
logger.addHandler(ch)

exmo_watcher = ExchangeWatcher('exmo', 'BTC/USD')
bitfin_watcher = ExchangeWatcher('bitfinex', 'BTC/USD')
data = DataHistoryManager(bitfin_watcher, exmo_watcher)
btf = BitfinexBookWatcher()
fnd = FundingWatcher("XBTUSD")

alert = False
orderbook_alert = False


def send_prices(bot, update):
    message = ("Цены <b>BTC/USD</b>:\n" +
               "<i>Bitfinex</i> <b>{1:>8.2f}</b> USD, <i>спред:</i> <b>{4:.2f}</b>\n" +
               "<i>Exmo</i> <b>{0:>12.2f}</b> USD, <i>спред:</i> <b>{5:.2f}</b>\n" +
               "<i>разница:</i>  <b>{2:>7.2f}</b> USD (<b>{3:.3f}%</b>)").format(
        data.secondary.price,
        data.primary.price,
        data.diff_ma_fast,
        data.percent,
        data.primary.spread,
        data.secondary.spread
    )
    events.event_info("Price request", update, message)
    bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode=ParseMode.HTML)


def send_orderbook(bot, update):
    events.debug_info(bot, update)
    bid_total = btf.bid_depth
    bids = sorted(btf.bids.keys())
    bids_price_range = abs(round(float(bids[0]) - float(bids[-1])))
    ask_total = btf.ask_depth
    asks = sorted(btf.asks.keys())
    asks_price_range = abs(round(float(asks[0]) - float(asks[-1])))
    depth_total = bid_total + ask_total
    message = ("<b>BTC/USD</b> стаканы <i>Bitfinex</i>:\n" +
               "<pre>     Покупка | Продажа \n" +
               "{8:>10.0f} % | {9:<3.0f}%\n" +
               "{0:>12.2f} | {3:<12.2f}\n" +
               "({1:4.0f}..{2:4.0f}) | ({4:4.0f}..{5:4.0f})\n" +
               "  |-{6:4.0f}-|       |-{7:4.0f}-|</pre>").format(
        bid_total,
        float(bids[0]),
        float(bids[-1]),
        ask_total,
        float(asks[0]),
        float(asks[-1]),
        bids_price_range,
        asks_price_range,
        bid_total / depth_total * 100,
        ask_total / depth_total * 100
    )
    events.event_info("Orderbook request", update, message)
    bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode=ParseMode.HTML)


def send_orderbook_graph(bot, update):
    target_file = '{0}_ob.png'.format(update.message.chat_id)
    graph.generate_book_graph(target_file, btf)
    events.event_info("Orderbook graph request", update, "target file: " + target_file)
    bot.sendChatAction(chat_id=update.message.chat_id, action=ChatAction.UPLOAD_PHOTO)
    bot.send_photo(chat_id=update.message.chat_id, photo=open(target_file, 'rb'))
    os.remove(target_file)


def send_funding_graph(bot, update):
    target_file = '{0}_fn.png'.format(update.message.chat_id)
    graph.generate_funding_graph(target_file, fnd)
    events.event_info("Funding graph request", update, "target file: " + target_file)
    bot.sendChatAction(chat_id=update.message.chat_id, action=ChatAction.UPLOAD_PHOTO)
    bot.send_photo(chat_id=update.message.chat_id, photo=open(target_file, 'rb'))
    os.remove(target_file)


def add_message_handlers(disp):
    logger.info("Adding message handlers.")
    welcome_handler = MessageHandler(Filters.status_update.new_chat_members, events.welcome)
    disp.add_handler(welcome_handler)

    mention_handler = MessageHandler(Filters.entity(MessageEntity.MENTION), events.mention)
    disp.add_handler(mention_handler)

    el_handler = MessageHandler(Filters.regex(r"\s*Эля\s*"), events.el)
    disp.add_handler(el_handler)

    el_bday_handler = MessageHandler(Filters.regex(r"\s*сегодня день\s*"), events.el_bday)
    disp.add_handler(el_bday_handler)

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

    adv_graph_handler = CommandHandler('advgraph', events.send_advanced_graph, pass_args=True)
    disp.add_handler(adv_graph_handler)

    history_handler = CommandHandler('history', events.history, pass_args=True)
    disp.add_handler(history_handler)

    joke_handler = CommandHandler('joke', events.joke)
    disp.add_handler(joke_handler)

    ob_handler = CommandHandler('orderbook', send_orderbook)
    disp.add_handler(ob_handler)

    ob_graph_handler = CommandHandler('book', send_orderbook_graph)
    disp.add_handler(ob_graph_handler)
    fn_graph_handler = CommandHandler('funding', send_funding_graph)
    disp.add_handler(fn_graph_handler)

    # should be added as the LAST handler
    unknown_handler = MessageHandler(Filters.command, events.unknown)
    disp.add_handler(unknown_handler)


def callback_funding_updates(bot, job):
    fnd.update()


def callback_orderbook_updates(bot, job):
    btf.get_updates()
    # TODO: analyze the order book and send signal to subscribers if there are significant changes


def callback_exchanges_data(bot, job):
    global alert, btf
    data.update()
    if len(data.history) > 1:
        price_diff_prev = data.history[-2][4]
    else:
        price_diff_prev = data.history[-1][4]

    percent = data.percent
    logger.debug(
        "Avg price: {0}, Exmo price: {1}, Bitfinex price: {2}, diff: {3} ({4}%)".format(
            round(data.avg_ma_fast, 2),
            data.secondary.price,
            data.primary.price,
            data.diff,
            percent))

    if data.diff_ma_fast * price_diff_prev < 0:
        excl = emoji.emojize(":bangbang:", use_aliases=True)
        text = excl + "Внимание, Сменила знак разница цен BTC/USD между Bitfinex и Exmo. Было {0}, стало {1} USD".format(
            round(price_diff_prev, 2), round(data.diff_ma_fast, 2))
        send_text_to_subscribers(bot, text)
        logger.info("Alert is now True. Alert messages sent! Text: {0}".format(text))
        alert = True
    else:
        if (math.fabs(percent) <= 0.2) or (1 < percent < 3.0) or (1.8 < -percent < 3.0) or (0.5 < percent < 0.65):
            excl = emoji.emojize(":exclamation:", use_aliases=True)
            if not alert:
                text = excl + "Внимание" + excl + " Разница цен BTC/USD между Bitfinex и Exmo достигла {0}%, а именно {1} USD".format(
                    percent, round(data.diff_ma_fast, 2))
                send_text_to_subscribers(bot, text)
                logger.info("Alert is now True. Alert messages sent! Text: {0}".format(text))
                alert = True
        else:
            logger.debug("Alert is now False. Looking for new triggers.")
            alert = False

    # write values to exchange history file
    header = list(data.header)
    header.extend(
        ["{} spread".format(data.secondary.ex.name),
         "{} spread".format(data.primary.ex.name),
         "Price diff alert",
         "Bitfinex bids",
         "Bitfinex asks",
         "Bitfinex orderbook alert"]
    )
    header_text = ','.join(header)
    csv_list = [str(item) for item in data.history[-1]]
    csv_list.extend(
        [str(round(data.secondary.spread, 4)),
         str(round(data.primary.spread, 4)),
         str(alert),
         str(round(btf.bid_depth, 4)),
         str(round(btf.ask_depth, 4)),
         str(orderbook_alert)]
    )
    csv = ','.join(csv_list)
    write_exchange_data_to_file(header_text + "\n", csv + "\n")
    logger.debug("Bitfinex websocket connected: " + str(btf.wss.conn.connected.is_set()))
    logger.debug("Bitfinex websocket is alive: " + str(btf.wss.conn.is_alive()))
    if not (btf.wss.conn.connected.is_set() and btf.wss.conn.is_alive()):
        logger.warning("Bitfinex websocket is not connected! Trying to reconnect")
        del btf.wss
        del btf
        btf = BitfinexBookWatcher()
        logger.info("Starting the client")
        btf.start()
        logger.info("Connected: " + str(btf.wss.conn.connected.is_set()))


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
    try:
        f = open(full_path, "a+")
        if not exists:
            logger.info("file '" + full_path + "' does not exist. Writing header")
            f.write(header)
        logger.debug("filename with exchange data: " + data_filename)
        f.write(text)
    except:
        logger.debug("Exception occured")
    finally:
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
    logger.info("init regular job to get funding rate every minute")
    job__funding_minute = job_queue.run_repeating(callback_funding_updates, interval=60, first=0)
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
