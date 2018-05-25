import configparser
import logging
import os

logger = logging.getLogger('bot-service.configmanager')
config_object = configparser.ConfigParser()
config_object.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'))
config = config_object['MAIN']
