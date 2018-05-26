#!/bin/bash

SERVICE_DIR=/usr/local/bin/bot-service

cd $SERVICE_DIR
source $SERVICE_DIR/bot_env/bin/activate
cd $SERVICE_DIR/coinsneaker

python3 ./bot_service.py
