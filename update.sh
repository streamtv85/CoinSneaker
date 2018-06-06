#!/bin/bash


SERVICE_DIR=/usr/local/bin/bot-service
HOME_DIR=~/CoinSneaker

echo Killing bot instance
sudo pkill screen && echo Killed the bot || echo Nothing to kill

echo Updating the code from Git
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
echo Updating python modules
pip install -e . || echo failure installing packages
deactivate
echo Starting the bot...
screen -S bot -d -m $SERVICE_DIR/run.sh && echo The bot has started || echo problem starting the bot instance! Check logs for details
