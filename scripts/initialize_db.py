#!/usr/bin/env python3
"""ایجاد پایگاه داده و مدیر اولیه"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.connection import init_db, get_session
from database.models import Admin
from config import INITIAL_ADMIN_IDS
from utils.logging_config import setup_logging

logger = setup_logging()


def main():
    logger.info("ایجاد جداول پایگاه داده...")
    init_db()
    with get_session() as session:
        for tid in INITIAL_ADMIN_IDS:
            existing = session.query(Admin).filter(Admin.telegram_id == tid).first()
            if not existing:
                session.add(Admin(telegram_id=tid, role="super", full_name="Initial Admin"))
                logger.info("مدیر اولیه اضافه شد: %s", tid)
            else:
                logger.info("مدیر از قبل وجود دارد: %s", tid)
    logger.info("پایگاه داده آماده است.")


if __name__ == "__main__":
    main()
