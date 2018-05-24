import configparser
import logging

logger = logging.getLogger('bot-service.configmanager')
config_object = configparser.ConfigParser()
config_object.read('config.ini')
config = config_object['MAIN']
