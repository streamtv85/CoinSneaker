from setuptools import setup

setup(name='coinsneaker',
      version='0.4',
      description='Telegram bot for crypto analytics',
      url='https://github.com/streamtv85/CoinSneaker',
      author='streamtv85',
      author_email='streamtv85@gmail.com',
      license='MIT',
      packages=['coinsneaker'],
      install_requires=[
          'emoji',
          'requests',
          'python-telegram-bot',
          'matplotlib',
          'numpy',
          'ccxt',
          'btfxwss', 'arrow'
      ],
      zip_safe=False)
