"""نقطه ورود اصلی ربات"""
import sys
import time
from telebot import TeleBot
from config import BOT_TOKEN
from utils.logging_config import setup_logging
from database.connection import init_db, get_session
from bot.user_handlers import register_user_handlers
from bot.admin_handlers import register_admin_handlers
from bot.ai_handlers import register_ai_handlers

logger = setup_logging()


def create_bot() -> TeleBot:
    if not BOT_TOKEN or BOT_TOKEN.startswith("123456"):
        logger.error("BOT_TOKEN تنظیم نشده است. فایل .env را بررسی کنید.")
        sys.exit(1)
    bot = TeleBot(BOT_TOKEN, parse_mode=None)
    register_user_handlers(bot)
    register_admin_handlers(bot)
    register_ai_handlers(bot)
    return bot


def main():
    logger.info("در حال راه‌اندازی ربات...")
    init_db()
    logger.info("پایگاه داده آماده است.")

    # ساخت ایندکس RAG در صورت وجود داده
    try:
        from services.ai.ai_service import rebuild_ai_index
        with get_session() as session:
            n = rebuild_ai_index(session)
            logger.info("نمایه AI آماده شد (%s بخش).", n)
    except Exception as e:
        logger.warning("بازسازی نمایه AI ناموفق: %s", e)

    bot = create_bot()
    logger.info("ربات شروع به کار کرد (Long Polling)...")

    while True:
        try:
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=40,
                skip_pending=True,
                logger_level=None,
            )
        except KeyboardInterrupt:
            logger.info("ربات متوقف شد.")
            break
        except Exception as e:
            logger.error("خطای ارتباط با تلگرام: %s", e)
            logger.info("۱۰ ثانیه بعد دوباره تلاش می‌شود...")
            time.sleep(10)


if __name__ == "__main__":
    main()
