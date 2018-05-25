import configparser
import logging
import os

logger = logging.getLogger('bot-service.configmanager')
config_object = configparser.ConfigParser()
configfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
assert os.path.exists(configfile), "Couldn't find config file at: " + configfile
logger.info("loading config from: " + configfile)
config_object.read(configfile)
config = config_object['MAIN']
