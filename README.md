# CoinSneaker
Telegram bot to fetch different data from crypto exchanges

Written on python

Tested OS: Ubuntu 16.04 LTS

## How To install:

In commandline, run:
```
curl -L https://github.com/streamtv85/CoinSneaker/raw/master/install.sh | bash
```

#### Edit config file:

Go to `/usr/local/bin/bot-service/coinsneaker/config.ini`
and put your bot's token at `token=` line

## How to run:
#### In console mode so it is writing messages to the stdout:
```
/usr/local/bin/bot-service/run.sh
```

#### In detached mode using 'screen'
```
screen -S bot -d -m /usr/local/bin/bot-service/run.sh
```

### To autostart the bot on reboot:
```
crontab -e
```
then add line:
```
@reboot ( sleep 90 ; screen -S bot -d -m /usr/local/bin/bot-service/run.sh )
```

or, in commandline:
```
echo @reboot ( sleep 90 ; screen -S bot -d -m /usr/local/bin/bot-service/run.sh ) > crontab-fragment.txt
crontab -l | cat - crontab-fragment.txt >crontab.txt && crontab crontab.txt
```

### Working with screen sessions:

to attach to the session:
```
screen -x bot
```
to detach: press `Ctrl-A D`

to stop the bot:
either
```
pkill screen
```
or
```
screen -XS bot quit
```

Log file is located at
```
/usr/local/bin/bot-service/coinsneaker/bot-service.log
```

you can monitor the output with
```
tail -f /usr/local/bin/bot-service/coinsneaker/bot-service.log
```
## Update the bot to the current version from GitHub:

either:
```
/usr/local/bin/bot-service/update.sh
```
or (better)
```
curl -L https://github.com/streamtv85/CoinSneaker/raw/master/update.sh | bash
```
## Telegram commands:

- subscribe - Receive notifications when prices reach certain levels
- unsubscribe - Stop receiving notifications
- price - Get current BTC/USD prices
