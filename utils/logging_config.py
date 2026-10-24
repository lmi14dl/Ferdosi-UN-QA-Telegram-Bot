"""پیکربندی لاگینگ"""
import logging
import sys
from config import LOG_LEVEL


def setup_logging():
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("bot.log", encoding="utf-8"),
        ],
    )
    # کاهش نویز کتابخانه‌ها
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("TeleBot").setLevel(logging.INFO)
    return logging.getLogger("telegram_qa_bot")
