import math
import random
import time
import ccxt

import requests
import logging

from btfxwss import BtfxWss

logger = logging.getLogger('bot-service.exchange')
# time.clock()
start = time.time()
timestamp = 0.0


def get_price_diff_mock():
    global timestamp, start
    period = 300.0
    amp = 300.0
    timestamp = time.time() - start
    # logger.info("timestamp: {0}".format(timestamp))
    return round(- amp * math.sin(2 * math.pi * timestamp / period) + random.gauss(0, amp / 5), 2)
    # return round(amp * math.sin(2 * math.pi * timestamp * period) + random.gauss(0, amp / 10), 2)


def get_price_avg():
    return round((get_bitfinex_btc_price() + get_exmo_btc_price()) / 2, 2)


def get_exmo_btc_price():
    data = get_data_from_api("https://api.exmo.com", "/v1/ticker/")
    return round(float(data['BTC_USD']['last_trade']), 2)


def get_bitfinex_btc_price():
    data = get_data_from_api("https://api.bitfinex.com", "/v2/ticker/tBTCUSD")
    return round(float(data[6]), 2)


def get_data_from_api(base_url, path):
    response = requests.get(base_url + path)
    assert response.status_code == 200, logger.error(
        "Status code was {0} when accessing {1}".format(response.status_code, base_url + path))
    logger.debug("response from " + base_url + path)
    logger.debug(response.json())
    return response.json()


def update_ma(new_value, old_value, period):
    if old_value == 0:
        old_value = new_value
    return (new_value + period * old_value) / (period + 1)


class ExchangeWatcher:
    def __init__(self, exchange, symbol):
        self.price = 0
        self.volume = 0
        self.volume_ma8 = 0
        self.bid = 0
        self.ask = 0
        self.spread = 0
        self.ma60 = 0
        self.ma150 = 0
        self.ex = getattr(ccxt, exchange)({'enableRateLimit': True, 'verbose': False})
        assert self.ex.has['publicAPI'], "Exchange {0} doesn't have public API!".format(self.ex.name)
        assert self.ex.has['fetchTicker'], "Exchange {0} doesn't have ticker API!".format(self.ex.name)
        self.symbol = None
        # we do it this way because on Bitfinex there is no BTC/USD pair but BTC/USDT
        for key in sorted(self.ex.load_markets().keys()):
            if symbol in key:
                self.symbol = key
                break
        if not self.symbol:
            raise ValueError("symbol {0} hasn't been found on {1} exchange!".format(symbol, exchange))

    def update(self):
        ticker = self.ex.fetch_ticker(self.symbol)
        self.price = ticker['last']
        self.ask = ticker['ask']
        self.bid = ticker['bid']
        self.spread = self.ask - self.bid
        self.volume = ticker['baseVolume']
        self.ma60 = self.update_ma(self.price, self.ma60, 60)
        self.ma150 = self.update_ma(self.price, self.ma150, 150)
        self.volume_ma8 = self.update_ma(self.volume, self.volume_ma8, 8)

    @staticmethod
    def update_ma(new_value, old_value, period):
        if old_value == 0:
            old_value = new_value
        return (new_value + period * old_value) / (period + 1)


class DataHistoryManager:

    def __init__(self, primary: ExchangeWatcher, secondary: ExchangeWatcher):
        self.primary = primary  # Bitfinex
        self.secondary = secondary  # Exmo
        self.diff = 0
        self.percent = 0
        self.avg = 0
        self.avg_ma_fast = 0
        self.diff_ma_slow = 0
        self.diff_ma_fast = 0
        self.history = []

        self.ma_period_slow = 20
        self.ma_period_fast = 3
        self.max_history = 120
        self.header = ["Timestamp",
                       "{} price".format(self.secondary.ex.name),
                       "{} price".format(self.primary.ex.name),
                       "price diff",
                       "diff MA{}".format(self.ma_period_fast),
                       "diff MA{}".format(self.ma_period_slow),
                       "diff percent",
                       "{} volume".format(self.secondary.ex.name),
                       "{} volume".format(self.primary.ex.name),
                       "alert",
                       "\n",
                       ]
        print(','.join(self.header))

    def update(self):
        self.primary.update()
        self.secondary.update()
        self.diff = round(self.primary.price - self.secondary.price, 2)
        self.avg = round((self.primary.price + self.secondary.price) / 2, 2)
        self.avg_ma_fast = ExchangeWatcher.update_ma(self.avg, self.avg_ma_fast, self.ma_period_fast)
        # MA(diff) and diff(MA) should be the same actually
        self.diff_ma_slow = ExchangeWatcher.update_ma(self.diff, self.diff_ma_slow, self.ma_period_slow)
        self.diff_ma_fast = ExchangeWatcher.update_ma(self.diff, self.diff_ma_fast, self.ma_period_fast)
        self.percent = round(self.diff_ma_fast / self.avg_ma_fast * 100, 3)
        ticker = [
            time.strftime("%c"),
            self.secondary.price,
            self.primary.price,
            self.diff,
            round(self.diff_ma_fast, 2),
            round(self.diff_ma_slow, 2),
            self.percent,
            self.secondary.volume,
            self.primary.volume,
        ]
        self.history.append(ticker)
        # Limiting history size to certain amount (to speed up graph command)
        if len(self.history) > 120:
            self.history.pop(0)


class BitfinexWebsocketWatcher:

    def __init__(self):
        self.wss = BtfxWss()
        self.wss.start()
        while not self.wss.conn.connected.is_set():
            time.sleep(1)
        self.book_q = None
        time.sleep(2)

    def start(self):
        # for P1 precision usual width of order book is ~100 USD (for BTC/USD price ~6500)
        # for wider range (about 1500 USD) use P2 precision. But the price will be rounded to tens
        self.wss.subscribe_to_order_book('BTCUSD', prec="P1", len=100)

    def has_updates(self):
        self.book_q = self.wss.books('BTCUSD')  # returns a Queue object for the pair.
        return not self.book_q.empty()

    def get_updates(self):
        self.book_q = self.wss.books('BTCUSD')  # returns a Queue object for the pair.
        result = []
        while not self.book_q.empty():
            get = self.book_q.get()
            # print(get)
            result.append(get)
        return result

    def close(self):
        self.wss.unsubscribe_from_order_book('BTCUSD')
        self.wss.stop()


if __name__ == "__main__":

    # exmo_watcher = ExchangeWatcher('exmo', 'BTC/USDT')
    # bitfin_watcher = ExchangeWatcher('bitfinex', 'BTC/USDT')
    # data = DataHistoryManager(bitfin_watcher, exmo_watcher)
    # data.update()
    # data.update()
    # print("BTC price on Exmo: " + str(exmo_watcher.price) + " USD")
    # print("BTC price on Bitfinex: " + str(bitfin_watcher.price) + " USD")
    # print(data.history)

    bids = dict()
    asks = dict()


    def fill_the_book(input_list, bids_book: dict, asks_book: dict):
        for row in input_list:
            if isinstance(row[0], list):
                fill_the_book(row, bids_book, asks_book)
            else:
                price = str(row[0])
                count = row[1]
                amt = row[2]
                if count != 0:
                    if amt > 0:
                        bids_book[price] = amt
                    else:
                        asks_book[price] = abs(amt)

                else:
                    if amt > 0:
                        if price in bids_book.keys():
                            del (bids_book[price])
                    elif amt < 0:
                        if price in asks_book.keys():
                            del (asks_book[price])


    btf = BitfinexWebsocketWatcher()
    btf.start()
    print("socket connection opened. Waiting for 5 sec for initial data")
    time.sleep(5)
    for i in range(1, 5):
        upd = btf.get_updates()
        if upd:
            # print(upd)
            print("")
            for item in upd:
                book_item, tag = item
                fill_the_book(book_item, bids, asks)

            bid_depth = sum(bids.values())
            ask_depth = sum(asks.values())
            print("total: bids: {0}, asks: {1}".format(bid_depth, ask_depth))

        time.sleep(1)

    btf.close()
    print("")
    bid_prices = list(reversed(sorted(bids.keys())))
    # print("bids: " + str(len(bid_prices)))
    ask_prices = list(sorted(asks.keys()))
    # print("asks: " + str(len(ask_prices)))
    length = min(len(bid_prices), len(ask_prices))

    for i in range(length):
        print("%s: %s | %s: %s" % (bids[bid_prices[i]], bid_prices[i], ask_prices[i], asks[ask_prices[i]]))
