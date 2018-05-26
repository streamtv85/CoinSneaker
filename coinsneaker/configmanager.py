import configparser
import logging
import os

logger = logging.getLogger('bot-service.configmanager')
config_object = configparser.ConfigParser()
configfile = 'config.ini'
assert os.path.exists(configfile), "Couldn't find config file at: " + configfile
logger.info("loading config from: " + configfile)
config_object.read(configfile)
config = config_object['MAIN']
