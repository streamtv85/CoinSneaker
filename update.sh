#!/bin/sh


SERVICE_DIR=/usr/local/bin/bot-service
HOME_DIR=~/CoinSneaker

sudo pkill screen

cd ~
[ -d $HOME_DIR ] || git clone https://github.com/streamtv85/CoinSneaker.git
cd $HOME_DIR && git pull

[ -d $HOME_DIR ] || mkdir -p $SERVICE_DIR
\cp -rf $HOME_DIR/* $SERVICE_DIR
sudo chmod 755 $SERVICE_DIR/coinsneaker/bot_service.py
sudo chmod 755 $SERVICE_DIR/run.sh

screen -S bot -d -m /usr/local/bin/bot-service/run.sh