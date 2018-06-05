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
sudo chmod 755 $SERVICE_DIR/update.sh

#install any additional packages if needed
cd $SERVICE_DIR
source bot_env/bin/activate
pip install -e .
deactivate

screen -S bot -d -m $SERVICE_DIR/run.sh