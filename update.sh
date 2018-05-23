#!/bin/sh


SERVICE_DIR=/usr/local/bin/bot-service
HOME_DIR=~/CoinSneaker
DAEMON_NAME=bot-service

service $DAEMON_NAME stop



cd ~
[ -d $HOME_DIR ] || git clone https://github.com/streamtv85/CoinSneaker.git
cd ~/CoinSneaker
git pull https://github.com/streamtv85/CoinSneaker.git


mkdir -p $SERVICE_DIR
\cp -rf $HOME_DIR/* $SERVICE_DIR
sudo chmod 755 $SERVICE_DIR/bot/bot-service.py

sudo \cp -f $SERVICE_DIR/bot-service.sh /etc/init.d
sudo chmod 755 $SERVICE_DIR/bot-service.sh

service $DAEMON_NAME start
