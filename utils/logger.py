import os
import json
import logging.config

from telegram import Bot
from config import LOG_CFG, LOG_FILENAME, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN


def custom_logger(default_level='INFO'):
    path = LOG_CFG

    log_level = default_level
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        if LOG_FILENAME:
            config["handlers"]["log_file_handler"]["filename"] = LOG_FILENAME
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=log_level)

    return logging


def send_error(message: str) -> None:
    """
    텔레그램으로 에러 메시지를 발송한다
    :param message: Error message
    :return: None
    """

    bot = Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
