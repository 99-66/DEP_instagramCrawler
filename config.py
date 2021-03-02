import os
from datetime import datetime

DEV = False
PROJECT = 'instagramCrawler'
BASE_URL = 'https://www.instagram.com/{username}/'

# Multiprocess: processing count configuration
if DEV:
    proc_numbers = 2
    retry_proc_numbers = 2
else:
    proc_numbers = (os.cpu_count() * 2) + 1
    retry_proc_numbers = os.cpu_count()


# 수집 원천을 표시하기 위한 필드
SOURCE = 'instagram'
CRAWL_DATE = datetime.today()

# Redis Configuration
if DEV:
    REDIS = {
        'HOST': '',
        'PASSWORD': '',
        'PORT': 6379,
        'DB': 1,
        'ERROR_TABLE': 'error_table'
    }
else:
    REDIS = {
        'HOST': '',
        'PASSWORD': '',
        'PORT': 6379,
        'DB': 1,
        'ERROR_TABLE': 'error_table'
    }

# MongoDB Configuration
if DEV:
    MONGODB = {
        'HOST': '',
        'USER': '',
        'PASSWORD': '',
        'PORT': '27017',
        'SSL': False,
        'SSL_CA_CERTS': None,
        'REPLICA_SET': None,
        'COLLECTION': ''
    }
else:
    MONGODB = {
        'HOST': '',
        'USER': '',
        'PASSWORD': '',
        'PORT': '27017',
        'SSL': False,
        'SSL_CA_CERTS': None,
        'REPLICA_SET': None,
        'COLLECTION': ''
    }

# Logging Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_CFG = os.path.join(BASE_DIR, 'logging.json')
LOG_PATH = os.path.join(BASE_DIR, 'logs')
LOG_FILENAME = f'{LOG_PATH}/{PROJECT}.log'

if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)


# Telegram Configuration
TELEGRAM_TOKEN = ''
TELEGRAM_CHAT_ID = ''
