#!/bin/sh


SERVICE_DIR=/usr/local/bin/bot-service
HOME_DIR=~/CoinSneaker
#DAEMON_NAME=bot-service
CONFIG_FILE=config.ini
#PYTHONPATH=$SERVICE_DIR

#service $DAEMON_NAME stop

#Install dependencies
sudo apt-get -y update && sudo apt-get -y upgrade
# setting up python 3.6 on Ubuntu 16.04 LTS
#sudo apt-get -y install software-properties-common
#sudo add-apt-repository -y ppa:deadsnakes/ppa
#sudo apt-get -y update
#sudo apt-get -y install git nano python3.6
#sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.5 1
#sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 2

sudo apt-get -y install  python3-venv python3-pip
pip3 install virtualenv
#pip3 install --user pipenv


cd ~
[ -d $HOME_DIR ] || git clone https://github.com/streamtv85/CoinSneaker.git
cd $HOME_DIR && git pull

sudo mkdir -p $SERVICE_DIR
sudo chown $USER:$USER $SERVICE_DIR
\cp -rfv $HOME_DIR/* $SERVICE_DIR
cd $SERVICE_DIR

sudo chmod 755 coinsneaker/bot_service.py
sudo chmod 755 coinsneaker/run.sh
#sudo chmod 755 $SERVICE_DIR/bot-service.sh
#sudo \cp -f $SERVICE_DIR/bot-service.sh /etc/init.d

virtualenv -p python3 bot_env
source bot_env/bin/activate

pip install -e .

cd $SERVICE_DIR/coinsneaker
#Install python packages to virtualenv
#pipenv install requests python-telegram-bot emoji

#cd /etc/init.d
#sudo update-rc.d bot-service.sh defaults

#Generating sample config file

if [ ! -f ./$CONFIG_FILE ]
then
    echo [MAIN] >> ./$CONFIG_FILE
    echo token=YOURTOKEN_HERE >> ./$CONFIG_FILE
    echo logMaxAge=14 >> ./$CONFIG_FILE
    echo logLevel=INFO >> ./$CONFIG_FILE
    echo exchangeDataAge=7 >> ./$CONFIG_FILE
    echo csvFolder=data >> ./$CONFIG_FILE
    echo csvPrefix=exchange-data >> ./$CONFIG_FILE
    echo dbFolder=db >> ./$CONFIG_FILE
fi

#To start the program:
#pipenv run python bot_service.py


#service $DAEMON_NAME start

