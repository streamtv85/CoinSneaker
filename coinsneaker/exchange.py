import math
import random
import time
import ccxt

import requests
import logging

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
    def __init__(self, exchange, ticker):
        self.price = 0
        self.volume = 0
        self.volume_ma8 = 0
        self.bid = 0
        self.ask = 0
        self.spread = 0
        self.ma60 = 0
        self.ma150 = 0
        self.ex = getattr(ccxt, exchange)({'enableRateLimit': True, })
        assert self.ex.has['publicAPI'], "Exchange {0} doesn't have public API!".format(self.ex.name)
        assert self.ex.has['fetchTicker'], "Exchange {0} doesn't have public API!".format(self.ex.name)
        self.ticker = None
        # we do it this way because on Bitfinex there is no BTC/USD pair but BTC/USDT
        for key in sorted(self.ex.load_markets().keys()):
            if ticker in key:
                self.ticker = key
                break
        if not self.ticker:
            raise ValueError("Ticker {0} hasn't been found on {1} exchange!".format(ticker, exchange))
        self.update()

    def update(self):
        ticker = self.ex.fetch_ticker(self.ticker)
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
        self.secondary = secondary
        self.diff = round(self.primary.price - self.secondary.price, 2)


# some tests
if __name__ == "__main__":
    exmo_watcher = ExchangeWatcher('exmo', 'BTC/USD')
    bitfin_watcher = ExchangeWatcher('bitfinex', 'BTC/USD')
    exmo_watcher.update()
    bitfin_watcher.update()
    print("BTC price on Exmo: " + str(exmo_watcher.price) + " USD")
    print("BTC price on Bitfinex: " + str(bitfin_watcher.price) + " USD")

    exmo_ccxt = getattr(ccxt, 'exmo')()
    bitfin_ccxt = getattr(ccxt, 'bitfinex')()
    # print(exmo_ccxt.load_markets())
    # print(bitfin_ccxt.load_markets())
    print(exmo_ccxt.fetch_ticker('BTC/USD'))
    print(bitfin_ccxt.fetch_ticker('BTC/USDT'))
