import datetime
import math
import random
import time
import arrow
import ccxt
import requests
import logging
from btfxwss import BtfxWss
import bitmex
import numpy as np

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


#
# def get_price_avg():
#     return round((get_bitfinex_btc_price() + get_exmo_btc_price()) / 2, 2)
#
#
# def get_exmo_btc_price():
#     data = get_data_from_api("https://api.exmo.com", "/v1/ticker/")
#     return round(float(data['BTC_USD']['last_trade']), 2)
#
#
# def get_bitfinex_btc_price():
#     data = get_data_from_api("https://api.bitfinex.com", "/v2/ticker/tBTCUSD")
#     return round(float(data[6]), 2)


def get_data_from_api(base_url, path):
    response = requests.get(base_url + path)
    assert response.status_code == 200, logger.error(
        "Status code was {0} when accessing {1}".format(response.status_code, base_url + path))
    logger.debug("response from " + base_url + path)
    # logger.debug(response.json())
    return response.json()


def get_funding():
    client = bitmex.bitmex(test=False)
    # print(client.Funding.dir())
    result = client.Funding.Funding_get(symbol="XBTUSD", reverse=True, count=100).result()
    instr = client.Instrument.Instrument_get(symbol="XBTUSD", reverse=True).result()[0][0]
    # for item in instr.keys():
    #     if 'funding' in item:
    #         print("{}: {}".format(item, instr[item]))
    # print(instr['fundingTimestamp'])
    # print(instr['fundingRate'] * 100)

    result_array = np.array([[instr['fundingTimestamp']], [instr['fundingRate'] * 100]])
    # print(instr[0][0])
    history = np.array([[item['timestamp'] for item in result[0]], [item['fundingRate'] * 100 for item in result[0]]])
    # print(result_array)
    print(np.append(result_array, history, axis=1))
    # get the array of funding rates, store them into an array, append the upcoming funding (taken from Instrument)

    #first element is the upcoming funding!
    return np.append(result_array, history, axis=1)


def get_tx_list():
    '''
    https://gtrade.club/api/transfer
    list of transactions since the timestamp given
    https://gtrade.club/api/transfer/1531032560
    Top-10000 BTC addresses
    https://gtrade.club/api/rich
    info on the address
    https://gtrade.club/api/address/1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s

    :return:
    '''
    base = "https://gtrade.club/api/"
    satoshis = 10 ** 8
    result = get_data_from_api(base, "rich")
    # print(result)
    now = arrow.now().timestamp
    result_now = get_data_from_api(base, "transfer/" + str(now))
    before = arrow.now().shift(hours=-6).timestamp
    result_before = get_data_from_api(base, "transfer/" + str(before))
    print(result_before)
    if result_before['new']:
        for item in result_before['data']:
            btc_before = item['last_balance'] / satoshis
            btc_now = item['balance'] / satoshis
            diff = btc_now - btc_before
            if abs(diff) >= 150:
                print("address: {0} #{1}, was: {2:.0f}, now: {3:.0f}, diff: {4}, upd: {5}".format(item['address'],
                                                                                                  item['position'],
                                                                                                  btc_before, btc_now,
                                                                                                  diff,
                                                                                                  item['updated_at']))


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
        self.ma60 = update_ma(self.price, self.ma60, 60)
        self.ma150 = update_ma(self.price, self.ma150, 150)
        self.volume_ma8 = update_ma(self.volume, self.volume_ma8, 8)


class DataHistoryManager:

    def __init__(self, primary: ExchangeWatcher, secondary: ExchangeWatcher):
        self.primary = primary  # Bitfinex
        self.secondary = secondary  # Exmo
        self.diff = 0
        self.avg = 0
        self.avg_ma_fast = 0
        self.diff_ma_slow = 0
        self.diff_ma_fast = 0
        self.percent = 0
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
                       ]
        # print(','.join(self.header))

    def update(self):
        self.primary.update()
        self.secondary.update()
        self.diff = round(self.primary.price - self.secondary.price, 2)
        self.avg = round((self.primary.price + self.secondary.price) / 2, 2)
        self.avg_ma_fast = update_ma(self.avg, self.avg_ma_fast, self.ma_period_fast)
        # MA(diff) and diff(MA) should be the same actually
        self.diff_ma_slow = update_ma(self.diff, self.diff_ma_slow, self.ma_period_slow)
        self.diff_ma_fast = update_ma(self.diff, self.diff_ma_fast, self.ma_period_fast)
        self.percent = round(self.diff_ma_fast / self.avg_ma_fast * 100, 3)
        ticker = [
            time.strftime("%c"),
            self.secondary.price,
            self.primary.price,
            self.diff,
            round(self.diff_ma_fast, 2),
            round(self.diff_ma_slow, 2),
            self.percent,
            round(self.secondary.volume, 4),
            round(self.primary.volume, 4),
        ]
        self.history.append(ticker)
        # Limiting history size to certain amount (to speed up graph command)
        if len(self.history) > 120:
            self.history.pop(0)


class BitfinexBookWatcher:

    def __init__(self):
        self.bids = dict()
        self.asks = dict()
        self.bid_depth = 0
        self.bid_ma_slow = 0
        self.bid_ma_fast = 0
        self.ask_depth = 0
        self.ask_ma_slow = 0
        self.ask_ma_fast = 0
        self.wss = BtfxWss()

    def start(self):
        if not self.wss.conn.connected.is_set():
            logger.info("Starting Bitfinex websocket client")
            self.wss.start()
        while not self.wss.conn.connected.is_set():
            time.sleep(1)
        # for P1 precision usual width of order book is ~100 USD (for BTC/USD price ~6500)
        # for wider range (about 1500 USD) use P2 precision. But the price will be rounded to tens
        self.wss.subscribe_to_order_book('BTCUSD', prec="P1", len=100)
        logger.info("Subscribed to Order Book WSS channel")
        # waiting for a bit to receive the book snapshot
        time.sleep(2)

    # call get_updates regularly to clear the queue!! Otherwise you may get OutOfMemory errors
    def get_updates(self):
        book_q = self.wss.books('BTCUSD')  # returns a Queue object for the pair.
        # result = []
        while not book_q.empty():
            get = book_q.get()
            # print(get)
            # result.append(get)
            book_item, tag = get
            self.fill_the_book(book_item)
        self.bid_depth = sum(self.bids.values())
        self.bid_ma_fast = update_ma(self.bid_depth, self.bid_ma_fast, 5)
        self.bid_ma_slow = update_ma(self.bid_depth, self.bid_ma_slow, 90)
        self.ask_depth = sum(self.asks.values())
        self.ask_ma_fast = update_ma(self.ask_depth, self.ask_ma_fast, 5)
        self.ask_ma_slow = update_ma(self.ask_depth, self.ask_ma_slow, 90)
        logger.debug("Market depth: bids: {0}, ma5: {1} ma90: {2} |  asks: {3}, ma5: {4} ma90: {5}".format(
            round(self.bid_depth),
            round(self.bid_ma_fast),
            round(self.bid_ma_slow),
            round(self.ask_depth),
            round(self.ask_ma_fast),
            round(self.ask_ma_slow)
        ))
        # return result

    # better call stop() at the end of the program (and on TERM signal)
    def stop(self):
        if self.wss.conn.connected.is_set() and self.wss.channel_configs:
            logger.debug("unsubscribe")
            self.wss.unsubscribe_from_order_book('BTCUSD')
        if self.wss.conn.connected.is_set():
            logger.debug("stopping the socket")
            self.wss.stop()
            logger.debug("stopped.")

    def fill_the_book(self, input_list):
        for row in input_list:
            if isinstance(row[0], list):
                self.fill_the_book(row)
            else:
                price = str(row[0])
                count = row[1]
                amt = row[2]
                if count != 0:
                    if amt > 0:
                        self.bids[price] = amt
                    else:
                        self.asks[price] = abs(amt)
                else:
                    if amt > 0:
                        if price in self.bids.keys():
                            del (self.bids[price])
                    elif amt < 0:
                        if price in self.asks.keys():
                            del (self.asks[price])


if __name__ == "__main__":
    # get_tx_list()

    get_funding()

# exmo_watcher = ExchangeWatcher('exmo', 'BTC/USDT')
# bitfin_watcher = ExchangeWatcher('bitfinex', 'BTC/USDT')


# b_watcher = getattr(ccxt, 'binance')({'enableRateLimit': True, 'verbose': False})
# response = requests.get('https://api.binance.com/api/v1/time')
# print("server time: ")
# print(datetime.datetime.fromtimestamp(response.json()['serverTime']/1000).strftime('%Y-%m-%d %H:%M:%S.%f'))
# print("")
# candles = b_watcher.fetch_ohlcv(symbol='ETC/USDT', timeframe='1h', since=None)
# for candle in candles[-10:]:
#     # print(candle[0])
#     pass
#     print(datetime.datetime.fromtimestamp(candle[0]/1000).strftime('%Y-%m-%d %H:%M:%S.%f') + str(candle[1:]))
#
# exx = getattr(ccxt, 'exmo')({'enableRateLimit': True, 'verbose': False})
# ex_candles = exx.fetch_ohlcv(symbol='ETH/BTC', timeframe='1h', since=None)
# for candle in ex_candles[-10:]:
#     # print(candle[0])
#     pass
#     print(candle)


# data = DataHistoryManager(bitfin_watcher, exmo_watcher)
# data.update()
# data.update()
# print("BTC price on Exmo: " + str(exmo_watcher.price) + " USD")
# print("BTC price on Bitfinex: " + str(bitfin_watcher.price) + " USD")
# print(data.history)

# bids = dict()
# asks = dict()

# btf = BitfinexBookWatcher()
# btf.start()
# for i in range(1, 50):
#     btf.get_updates()
#     time.sleep(1)
#
# btf.stop()
