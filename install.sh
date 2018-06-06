#!/bin/bash


SERVICE_DIR=/usr/local/bin/bot-service
HOME_DIR=~/CoinSneaker
CONFIG_FILE=config.ini

echo Updating the system
sudo apt-get -y update && sudo apt-get -y upgrade

echo Installing dependencies
sudo apt-get -y install  python3-venv python3-pip
pip3 install virtualenv

echo Pulling the code from Git
cd ~
[ -d $HOME_DIR ] || git clone https://github.com/streamtv85/CoinSneaker.git
cd $HOME_DIR && git pull

sudo mkdir -p $SERVICE_DIR
sudo chown $USER:$USER $SERVICE_DIR
\cp -rfv $HOME_DIR/* $SERVICE_DIR
cd $SERVICE_DIR

sudo chmod 755 coinsneaker/bot_service.py
sudo chmod 755 ./run.sh
sudo chmod 755 ./update.sh

echo Creating virtual env
virtualenv -p python3 bot_env
source bot_env/bin/activate

echo Updating python modules
pip install -e . || echo failure installing packages
#pipenv install requests python-telegram-bot emoji

CONFIG_FILE=$SERVICE_DIR/coinsneaker/$CONFIG_FILE
if [ ! -f $CONFIG_FILE ]
then
    echo Generating sample config file
    echo [MAIN] >> $CONFIG_FILE
    echo token=YOURTOKEN_HERE >> $CONFIG_FILE
    echo logMaxAge=14 >> $CONFIG_FILE
    echo logLevel=INFO >> $CONFIG_FILE
    echo exchangeDataAge=7 >> $CONFIG_FILE
    echo csvFolder=data >> $CONFIG_FILE
    echo csvPrefix=exchange-data >> $CONFIG_FILE
    echo dbFolder=db >> $CONFIG_FILE
fi
