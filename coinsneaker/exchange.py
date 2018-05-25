import math
import random
import time

import requests  # fades.pypi
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
    return response.json()


def update_ma(new_value, old_value, period):
    if old_value == 0:
        old_value = new_value
    return (new_value + period * old_value) / (period + 1)


# some tests
if __name__ == "__main__":
    print("BTC price on Exmo: " + str(get_exmo_btc_price()) + " USD")
    print("BTC price on Bitfinex: " + str(get_bitfinex_btc_price()) + " USD")
