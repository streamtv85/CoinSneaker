#!/bin/bash


SERVICE_DIR=/usr/local/bin/bot-service
HOME_DIR=~/CoinSneaker
CONFIG_FILE=config.ini

#Install dependencies
sudo apt-get -y update && sudo apt-get -y upgrade

sudo apt-get -y install  python3-venv python3-pip
pip3 install virtualenv


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

#Install python packages to virtualenv
virtualenv -p python3 bot_env
source bot_env/bin/activate

pip install -e .
#pipenv install requests python-telegram-bot emoji

#Generating sample config file
CONFIG_FILE=$SERVICE_DIR/coinsneaker/$CONFIG_FILE
if [ ! -f $CONFIG_FILE ]
then
    echo [MAIN] >> $CONFIG_FILE
    echo token=YOURTOKEN_HERE >> $CONFIG_FILE
    echo logMaxAge=14 >> $CONFIG_FILE
    echo logLevel=INFO >> $CONFIG_FILE
    echo exchangeDataAge=7 >> $CONFIG_FILE
    echo csvFolder=data >> $CONFIG_FILE
    echo csvPrefix=exchange-data >> $CONFIG_FILE
    echo dbFolder=db >> $CONFIG_FILE
fi
