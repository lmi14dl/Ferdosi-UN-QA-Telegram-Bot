#!/usr/bin/env python3
"""واردسازی داده‌های اولیه از سه فایل منبع"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.connection import init_db, get_session
from services.import_service import run_full_import
from utils.logging_config import setup_logging

logger = setup_logging()


def main():
    logger.info("شروع واردسازی داده‌های اولیه...")
    init_db()
    with get_session() as session:
        report = run_full_import(session)
    print("\n" + report)
    logger.info("واردسازی به پایان رسید.")


if __name__ == "__main__":
    main()
