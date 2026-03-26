import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
GROUP_ID = int(os.getenv('GROUP_ID'))  # Добавить GROUP_ID

if not TOKEN or not ADMIN_ID or not GROUP_ID:
    raise ValueError("TOKEN, ADMIN_ID или GROUP_ID не найдены в .env файле!")

# Database settings
DB_NAME = 'bot_database.db'

# Default settings for orders
DEFAULT_SETTINGS = {
    'subs_price': 5.0,
    'subs_min_qty': 1000,
    'subs_max_qty': 1000000,
    'subs_min_hrs': 0,
    'subs_max_hrs': 200,
    'min_deposit': 5.0
}

# View tariffs
DEFAULT_TARIFFS = [
    ('1k', 2.0, 10*24*3600),
    ('5k', 7.5, 10*24*3600),
    ('10k', 13.0, 10*24*3600),
    ('15k', 17.5, 10*24*3600),
    ('20k', 22.0, 10*24*3600)
]

# Crypto addresses
CRYPTO_ADDRESSES = {
    "USDT": "TJH1kg6w5qXupx4nQ9keCQUFxkEUJXvubG",
    "BTC": "163hvzR8NGyGkjcwDbgqG3B5jfk8TcYWRx",
    "LTC": "LZdEEnowWPfrzC4FNWi7Z5t8Uzjffu1vNK",
    "ETH": "0x4c76fb5e2978797a4ad45eef0f9b58ea94bf6d89"
}

# Tariff views mapping
TARIFF_VIEWS_MAP = {
    '1k': 1000,
    '5k': 5000,
    '10k': 10000,
    '15k': 15000,
    '20k': 20000
}