#!/usr/bin/env python3
"""پشتیبان‌گیری از پایگاه داده SQLite"""
import sys
import shutil
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR, DATABASE_URL

def main():
    # استخراج مسیر فایل از URL
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = Path(DATABASE_URL.replace("sqlite:///", ""))
        if not db_path.is_absolute():
            db_path = Path(__file__).resolve().parent.parent / db_path
    else:
        print("فقط SQLite پشتیبانی می‌شود.")
        sys.exit(1)

    if not db_path.exists():
        print(f"فایل پایگاه داده یافت نشد: {db_path}")
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DATA_DIR / f"bot_backup_{stamp}.db"
    shutil.copy2(db_path, backup_path)
    print(f"✅ پشتیبان ذخیره شد: {backup_path}")


if __name__ == "__main__":
    main()
