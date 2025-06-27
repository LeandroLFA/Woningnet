import os

USERNAME = os.environ.get('WN_USERNAME', 'leandro.derby@outlook.com')
PASSWORD = os.environ.get('WN_PASSWORD', '_dele8021LD')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', "7780567041:AAF9799ZH3sXKm6yQe5gxRAXOQjHvW6GMfg")
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', "1618177476")
MIN_HUUR = 600
MAX_HUUR = 1250
MIN_OPPERVLAKTE = 50
MIN_KAMERS = 2
MAX_KAMERS = 5
CHECK_INTERVAL = 1 * 60  # 15 minutes (seconds)
DATA_DIR = "data"
FOUND_FILE = os.path.join(DATA_DIR, "gevonden.json")
VISITED_FILE = os.path.join(DATA_DIR, "gereageerd.json")