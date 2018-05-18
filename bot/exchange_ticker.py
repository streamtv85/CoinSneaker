import math
import random
import time

import requests
import logging

logger = logging.getLogger('bot-service.exchange')
# time.clock()
start = time.time()
timestamp = 0.0


def get_price_diff(mock=False):
    global timestamp, start
    if mock:
        period = 300.0
        amp = 300.0
        timestamp = time.time() - start
        logger.info("timestamp: {0}".format(timestamp))
        return round(amp * math.sin(2 * math.pi * timestamp / period) + random.gauss(0, amp / 5), 2)
        # return round(amp * math.sin(2 * math.pi * timestamp * period) + random.gauss(0, amp / 10), 2)

    return round(get_bitfinex_btc_price() - get_exmo_btc_price(), 2)


def get_exmo_btc_price():
    data = get_data_from_api("https://api.exmo.com", "/v1/ticker/")
    return round(float(data['BTC_USD']['last_trade']), 2)


def get_bitfinex_btc_price():
    data = get_data_from_api("https://api.bitfinex.com", "/v2/ticker/tBTCUSD")
    return round(float(data[6]), 2)


def get_data_from_api(base_url, path):
    response = requests.get(base_url + path)
    assert response.status_code == 200, logger.error("Status code was unsuccessful!")
    return response.json()


print("BTC price on Exmo: " + str(get_exmo_btc_price()) + " USD")
print("BTC price on Bitfinex: " + str(get_bitfinex_btc_price()) + " USD")

# step = 1  # seconds
# while True:
#     print(get_price_diff(mock=True))
#     time.sleep(step)
