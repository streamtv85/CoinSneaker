#!/bin/sh


SERVICE_DIR=/usr/local/bin/bot-service

#DAEMON_NAME=bot-service


#sudo chmod 755 $SERVICE_DIR/coinsneaker/bot_service.py

#To start the program:

cd $SERVICE_DIR
source bot_env/bin/activate
cd $SERVICE_DIR/coinsneaker

python3 ./bot_service.py
