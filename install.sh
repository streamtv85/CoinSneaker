#!/bin/sh


SERVICE_DIR=/usr/local/bin/bot-service
HOME_DIR=~/CoinSneaker
DAEMON_NAME=bot-service
#PYTHONPATH=$SERVICE_DIR

#service $DAEMON_NAME stop

sudo apt-get -y update && sudo apt-get -y upgrade
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get -y update
sudo apt-get -y install python3.6  python3-venv python3-pip
pip install --user pipenv

cd ~
[ -d $HOME_DIR ] || git clone https://github.com/streamtv85/CoinSneaker.git
cd $HOME_DIR && git pull

sudo mkdir -p $SERVICE_DIR
sudo chown administrator $SERVICE_DIR
\cp -rf $HOME_DIR/* $SERVICE_DIR
sudo chmod 755 $SERVICE_DIR/bot/bot-service.py

sudo \cp -f $SERVICE_DIR/bot-service.sh /etc/init.d
sudo chmod 755 $SERVICE_DIR/bot-service.sh

cd $SERVICE_DIR
pipenv install requests python-telegram-bot emoji
pipenv install -e .


#service $DAEMON_NAME start

