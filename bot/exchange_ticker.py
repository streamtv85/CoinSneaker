import requests
import logging

logger = logging.getLogger('bot-service.exchange')


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
