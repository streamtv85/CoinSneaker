# CoinSneaker
Telegram bot to fetch different data from crypto exchanges


How To install:

curl -L https://github.com/streamtv85/CoinSneaker/raw/master/install.sh | bash

Go to /usr/local/bin/bot-service/coinsneaker/config.ini
and put your bot's token at 'token=' line

How to run:
In console mode so it is writing messages to the stdout:
/usr/local/bin/bot-service/run.sh

In detached mode using 'screen'
screen -S bot -d -m /usr/local/bin/bot-service/run.sh

to attach later:
screen -x bot

to detach: press Ctrl-A D

to stop the bot:
either pkill screen
or
screen -XS bot quit

Log is at
/usr/local/bin/bot-service/coinsneaker/bot-service.log

you can monitor the output with
tail -f /usr/local/bin/bot-service/coinsneaker/bot-service.log

Update the bot to the current version from GitHub:

either:
/usr/local/bin/bot-service/update.sh
or
curl -L https://github.com/streamtv85/CoinSneaker/raw/master/update.sh | bash

Telegram commands:

subscribe - Receive notifications when prices reach certain levels
unsubscribe - Stop receiving notifications
price - Get current BTC/USD prices