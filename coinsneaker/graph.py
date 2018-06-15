import datetime
import glob
import os
import time
import logging
import matplotlib

matplotlib.use('Agg')
import numpy
import matplotlib.pyplot as plt
import matplotlib.dates
from coinsneaker.configmanager import config

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


def get_data_from_file(size):
    found_files = get_exchange_data_files()
    data_filename = found_files[0]
    my_data = numpy.genfromtxt(data_filename, delimiter=',', skip_header=1, dtype=None, encoding=None,
                               usecols=[0, 1, 2, 3, 4, 5, 6, 7])
    output = my_data[-size:]
    # if not enough data in the last file, we try to get additional data from the previous one
    if (len(my_data) < size) and len(found_files) > 1:
        logger.debug("Grabbing additional data from previous file {0}".format(found_files[1]))
        my_data_prev = numpy.genfromtxt(found_files[1], delimiter=',', skip_header=1, dtype=None, encoding=None,
                                        usecols=[0, 1, 2, 3, 4, 5, 6, 7])

        last_time_of_prev_file = time.mktime(time.strptime(my_data_prev['f0'][-1], "%c"))
        first_time_of_last_file = time.mktime(time.strptime(output['f0'][0], "%c"))
        # checking of there is not gap between csv files
        # in case of gap - don't take prev. file
        if first_time_of_last_file - last_time_of_prev_file < 90.0:
            output = numpy.concatenate((my_data_prev, my_data))[-size:]
    return output


def generate_graph(target_file, period, debug=False):
    max_size = period * 60
    my_data = get_data_from_file(max_size)
    if not len(my_data):
        return False
    fmt_dates = [matplotlib.dates.date2num(datetime.datetime.fromtimestamp(time.mktime(time.strptime(element, "%c"))))
                 for element in
                 my_data['f0'][-max_size:]]

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
    exmo_prices = my_data['f1'][-max_size:]
    bitfin_prices = my_data['f2'][-max_size:]
    if debug:
        alerts = my_data['f7'][-max_size:]
        ticks = list(bitfin_prices)
        for i, item in enumerate(fmt_dates):
            # print(str(i) + " " + str(item))
            if not alerts[i]:
                ticks[i] = None

    logger.debug("exmo size: " + str(len(exmo_prices)))
    logger.debug("bitfin size: " + str(len(bitfin_prices)))

    # fig = plt.figure(tight_layout=True)
    fig = plt.figure(figsize=(9.6, 7.2), tight_layout=True)
    # default size is 6.4 * 4.8 inches
    # print(fig.get_size_inches())
    ax = fig.add_subplot(111)
    ax.plot_date(fmt_dates, exmo_prices, fmt='b', label='Exmo')
    ax.plot_date(fmt_dates, bitfin_prices, fmt='g', label='Bitfinex')
    if debug:
        ax.plot_date(fmt_dates, ticks, fmt='r.')
    ax.set_ylabel('BTC/USD')
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%d-%m %H:%M'))
    ax2 = fig.add_subplot(2)
    ax2.plot_date(fmt_dates, exmo_prices)
    plt.legend()
    plt.grid()
    fig.align_labels()
    fig.autofmt_xdate()
    plt.savefig(target_file)
    return True


if __name__ == "__main__":
    generate_graph('1234322.png', 3)
    # get_data_from_file(120)
