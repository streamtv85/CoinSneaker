import datetime
import glob
import os
import time
import logging
import matplotlib

from coinsneaker.exchange import BitfinexBookWatcher, get_funding, FundingWatcher

matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates
from coinsneaker.configmanager import config
from coinsneaker.exchange import update_ma

logger = logging.getLogger('bot-service.graph')


def get_exchange_data_files():
    pattern = os.path.join(config.get('csvFolder'), config.get('csvPrefix') + "*.csv")
    found_files = glob.glob(pattern)
    found_files.sort(key=os.path.getmtime, reverse=True)
    if not len(found_files):
        logger.warning("No files with exchange data was found. Nothing to draw yet.")
        return []
    logger.debug("{0} is the last found file with exchange data".format(found_files[0]))
    return found_files


def get_data_from_file(size, found_files):
    data_filename = found_files[0]
    my_data = np.genfromtxt(data_filename, delimiter=',', skip_header=1, dtype=None, encoding=None)
    # if not enough data in the last file, we try to get additional data recursively from the previous one
    if (len(my_data) < size) and len(found_files) > 1:
        logger.debug("Grabbing additional data from previous file {0}".format(found_files[1]))
        my_data_prev = get_data_from_file(size - len(my_data), found_files[1:])
        output = np.concatenate((my_data_prev, my_data))[-size:]
    else:
        output = my_data[-size:]
    return output


def generate_graph(target_file, period, debug=False):
    max_size = period * 60  # convert hours to minutes
    found_files = get_exchange_data_files()
    my_data = get_data_from_file(max_size, found_files)
    if not len(my_data):
        return False
    fmt_dates = [matplotlib.dates.date2num(datetime.datetime.fromtimestamp(time.mktime(time.strptime(element, "%c"))))
                 for element in
                 my_data['f0']]

    if len(fmt_dates) < max_size:
        logger.info(
            "length of available data is below requested {0} minutes. Showing {1} minutes instead.".format(max_size,
                                                                                                           len(
                                                                                                               fmt_dates)))
        max_size = len(fmt_dates)
    logger.info("plotting graph for {0} minutes from {1} to {2} ".format(max_size,
                                                                         matplotlib.dates.num2date(
                                                                             fmt_dates[0]).strftime(
                                                                             "%d-%m_%H:%M"),
                                                                         matplotlib.dates.num2date(
                                                                             fmt_dates[-1]).strftime(
                                                                             "%d-%m_%H:%M")))
    logger.debug("dates size: " + str(len(fmt_dates)))
    exmo_prices = my_data['f1']
    bitfin_prices = my_data['f2']
    exmo_prices_ma = exmo_prices.copy()
    bitfin_prices_ma = bitfin_prices.copy()

    if debug:
        alerts = my_data['f11']
        alerts_prev = np.insert(alerts[:-1], 0, False)
        bitfin_spread = my_data['f10'] / 2
        bitfin_bids = my_data['f12']
        bitfin_asks = my_data['f13']
        exmo_spread = my_data['f9'] / 2
        percents = my_data['f6']
        ticks = percents.copy()
        percents_ma = percents.copy()
        percents_ma2 = percents.copy()
        # we put dots only when alert changes from false to true: if alerts[i] and not alerts[i - 1]
        ticks[np.logical_or(np.logical_not(alerts), alerts_prev)] = None
        ticks[0] = None

    for i in range(1, len(fmt_dates), 1):
        # print(str(i) + " " + str(item))
        exmo_prices_ma[i] = update_ma(exmo_prices[i], exmo_prices_ma[i - 1], 10)
        bitfin_prices_ma[i] = update_ma(bitfin_prices[i], bitfin_prices_ma[i - 1], 10)
        if debug:
            # if i > 0:
            # if alerts[i] and not alerts[i - 1]:
            #     pass
            # else:
            #     ticks[i] = None
            percents_ma[i] = update_ma(percents[i], percents_ma[i - 1], 3)
            percents_ma2[i] = update_ma(percents[i], percents_ma2[i - 1], 20)
            # exmo_spread[i] = exmo_spread[i] / 2
            if bitfin_bids[i] == 0:
                bitfin_bids[i] = bitfin_bids[i - 1]
            if bitfin_asks[i] == 0:
                bitfin_asks[i] = bitfin_asks[i - 1]

    logger.debug("exmo size: " + str(len(exmo_prices)))
    logger.debug("bitfin size: " + str(len(bitfin_prices)))
    scale_ratio = 1
    max_period_to_scale = 32
    if 2 <= period <= max_period_to_scale:
        scale_ratio = (2 * (period - 2) / (max_period_to_scale - 2)) + 1
    elif period > max_period_to_scale:
        scale_ratio = 3
    print(scale_ratio)
    if debug:
        fig = plt.figure(figsize=(9.6 * scale_ratio, 10.8), tight_layout=True)
        ax_main = fig.add_subplot(312)
    else:
        fig = plt.figure(figsize=(9.6 * scale_ratio, 7.4), tight_layout=True)
        ax_main = fig.add_subplot(111)
    # default size is 6.4 * 4.8 inches
    # print(fig.get_size_inches())

    ax_main.plot_date(fmt_dates, exmo_prices, fmt='c:')
    ax_main.plot_date(fmt_dates, bitfin_prices, fmt='g:')
    if debug:
        ax_main.errorbar(fmt_dates, exmo_prices_ma, exmo_spread, fmt='b', label='Exmo MA10')
        ax_main.errorbar(fmt_dates, bitfin_prices_ma, bitfin_spread, fmt='g', label='Bitfinex MA10')
    else:
        ax_main.plot_date(fmt_dates, exmo_prices_ma, fmt='b', label='Exmo MA10')
        ax_main.plot_date(fmt_dates, bitfin_prices_ma, fmt='g', label='Bitfinex MA10')
    ax_main.set_ylabel('BTC/USD')
    ax_main.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d-%m %H:%M'))
    ax_main.legend()
    ax_main.grid()

    if debug:
        # print(ticks)
        ax_percent = fig.add_subplot(311)
        ax_percent.plot_date(fmt_dates, percents, fmt='k', label='diff percent')
        ax_percent.plot_date(fmt_dates, percents_ma, fmt='k--', label='diff percent MA3')
        ax_percent.plot_date(fmt_dates, percents_ma2, fmt='m--', label='diff percent MA20')
        # ax_percent.plot_date(fmt_dates, percents2, fmt='m', label='diff percent from MA10 prices')
        ax_percent.plot_date(fmt_dates, ticks, fmt='ro', label='alerts')
        ax_percent.set_ylabel('percent')
        ax_vol = fig.add_subplot(313)
        ax_vol.plot_date(fmt_dates, bitfin_bids, fmt='g', label='Bitfinex bids', drawstyle='steps')
        ax_vol.plot_date(fmt_dates, bitfin_asks, fmt='r', label='Bitfinex asks', drawstyle='steps')
        ax_percent.legend()
        ax_vol.legend()
        ax_percent.grid()
        ax_vol.grid()
    # plt.subplots_adjust(bottom=0.1, right=0.8, top=0.9)
    # plt.legend()
    # plt.grid()
    fig.align_labels()
    fig.autofmt_xdate()
    plt.savefig(target_file)
    return True


def generate_book_graph(target_file, data: BitfinexBookWatcher):
    data_bids = sorted(data.bids.keys())
    bid_prices = [float(item) for item in data_bids]
    bids = [data.bids[price] for price in data_bids]
    max_bid = max(bids)
    data_asks = sorted(data.asks.keys())
    ask_prices = [float(item) for item in data_asks]
    asks = [data.asks[price] for price in data_asks]
    max_ask = max(asks)

    fig = plt.figure(figsize=(7.2, 9.6), tight_layout=True)
    ax_bid = fig.add_subplot(121)
    ax_bid.barh(bid_prices, bids, color='g')
    ax_ask = fig.add_subplot(122)
    ax_ask.barh(ask_prices, asks, color='r')

    ax_bid.set_title('Bids', color='g')
    ax_ask.set_title('Asks', color='r')
    ax_bid.set_xlim(max(max_bid, max_ask), 0)
    ax_bid.set_ylim(bid_prices[0], bid_prices[-1])
    ax_ask.set_xlim(0, max(max_bid, max_ask))
    ax_ask.set_ylim(ask_prices[-1], ask_prices[0])

    bid_ticks = bid_prices[0::10]
    bid_ticks.append(bid_prices[-1])
    ask_ticks = ask_prices[0::10]
    ask_ticks.append(ask_prices[-1])
    ax_bid.set_yticks(bid_ticks)
    ax_bid.tick_params(labelcolor='g')
    ax_ask.set_yticks(ask_ticks)
    ax_ask.tick_params(labelcolor='r')
    ax_ask.yaxis.set_ticks_position('right')

    ax_bid.grid()
    ax_ask.grid()
    plt.savefig(target_file)


def generate_funding_graph(target_file, data: FundingWatcher):
    # data = FundingWatcher("XBTUSD")
    fig = plt.figure(figsize=(9.6, 7.2), tight_layout=True)
    ax = fig.add_subplot(111)
    history_tail = data.history.tail(len(data.mean.dropna()))
    data_pos = history_tail[history_tail > 0]
    data_neg = history_tail[history_tail < 0]
    # data_mean = data.history.rolling(window=30).mean()
    # data_stdev = data.history.rolling(window=30).std()
    ax.bar(data_pos.index, data_pos, 0.25, color='r', label='Bearish funding rate')
    ax.bar(data_neg.index, data_neg, 0.25, color='b', label='Bullish funding rate')
    ax.bar(data.current.index[0], data.current[0], 0.25, color='#F4D03F', label='Next funding rate')
    ax.bar(data.current.index[-1], data.current[-1], 0.25, color='#AFAFAF', label='Predicted funding rate')
    ax.plot(data.mean.index, data.mean)
    ax.plot(data.lower.index, data.lower, color='r')
    ax.plot(data.higher.index, data.higher, color='b')
    ax.set_ylabel('percent')
    ax.legend()
    ax.grid()
    fig.align_labels()
    fig.autofmt_xdate()
    plt.savefig(target_file)


if __name__ == "__main__":
    # data = BitfinexBookWatcher()
    # data.start()
    # time.sleep(2)
    # data.get_updates()
    # time.sleep(1)
    # data.stop()
    # generate_book_graph("65464564.png", data)
    # generate_graph('1234322.png', 12)
    # generate_graph('1234322_debug.png', 2, debug=True)

    generate_funding_graph('111_funding.png')

    # get_data_from_file(120)
