#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت واردسازی خودکار داده‌های ربات
=====================================
با یک بار اجرا، سه فایل منبع را می‌خواند و تمام
دسته‌بندی‌ها، خدمات و پرسش‌وپاسخ‌ها را در دیتابیس ذخیره می‌کند.

نحوه اجرا:
    python import_data.py

فایل‌های مورد نیاز (یکی از مسیرهای زیر کافی است):
  - پوشه attachments کنار پروژه
  - همان پوشه‌ای که این اسکریپت در آن است
  - پوشه data
"""

import sys
import os
from pathlib import Path

# اطمینان از اینکه ماژول‌های پروژه پیدا شوند
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from database.connection import init_db, get_session, engine, Base
from database.models import Category, Question, Service, ContactPoint, ImportJob, Admin
from services.import_service import run_full_import
from importers.excel_importer import import_excel
from importers.word_importer import import_word
from importers.validate_import import generate_import_report
from config import INITIAL_ADMIN_IDS
from utils.logging_config import setup_logging

logger = setup_logging()


def find_file(filename: str) -> Path | None:
    """جستجوی فایل در چند مسیر رایج"""
    candidates = [
        ROOT / "attachments" / filename,
        ROOT.parent / "attachments" / filename,
        Path("/home/workdir/attachments") / filename,
        ROOT / filename,
        ROOT / "data" / filename,
        Path.cwd() / filename,
        Path.cwd() / "attachments" / filename,
        Path.home() / "Desktop" / "telegram_qa_bot" / "attachments" / filename,
        Path.home() / "Desktop" / "attachments" / filename,
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def main():
    print("=" * 60)
    print("  واردسازی داده‌های ربات پرسش‌وپاسخ سازمانی")
    print("=" * 60)
    print()

    # ۱. ایجاد جداول
    print("[1/4] ایجاد/بررسی پایگاه داده...")
    init_db()
    print("      ✓ پایگاه داده آماده است.\n")

    # ۲. پیدا کردن فایل‌ها
    print("[2/4] جستجوی فایل‌های منبع...")

    files = {
        "excel": (
            "ربات_تلگرامی_بیمه_تکمیلی_نهایی.xlsx",
            None,  # root_name
        ),
        "word_structure": (
            "ربات_تلگرامی_گروه_ساختار_سازمانی،_تامین_و_بکارگماری.docx",
            None,
        ),
        "word_welfare": (
            "فرم_جمع_آوری_اطلاعات_ربات_تلگرامی_—_اداره_نگهداشت_و_امور_رفاه.docx",
            "امور رفاهی و نگهداشت",
        ),
    }

    found = {}
    missing = []
    for key, (fname, root_name) in files.items():
        path = find_file(fname)
        if path:
            found[key] = (path, root_name)
            print(f"      ✓ پیدا شد: {path}")
        else:
            missing.append(fname)
            print(f"      ✗ یافت نشد: {fname}")

    if not found:
        print("\n❌ هیچ فایل منبعی پیدا نشد!")
        print("لطفاً سه فایل را در یکی از این مسیرها قرار دهید:")
        print(f"  - {ROOT / 'attachments'}")
        print(f"  - {ROOT}")
        print(f"  - {Path.cwd()}")
        sys.exit(1)

    if missing:
        print(f"\n⚠ هشدار: {len(missing)} فایل پیدا نشد (ادامه با فایل‌های موجود)")

    print()

    # ۳. واردسازی
    print("[3/4] واردسازی داده‌ها...")
    reports = []

    with get_session() as session:
        # مدیر اولیه
        for tid in INITIAL_ADMIN_IDS:
            existing = session.query(Admin).filter(Admin.telegram_id == tid).first()
            if not existing and tid:
                session.add(Admin(telegram_id=tid, role="super", full_name="Initial Admin"))
                print(f"      ✓ مدیر اولیه اضافه شد: {tid}")

        # اکسل بیمه
        if "excel" in found:
            path, _ = found["excel"]
            print(f"\n      → در حال خواندن اکسل: {path.name}")
            r = import_excel(session, path)
            reports.append(r)
            session.commit()
            print(f"        واردشده: {r['imported']} | ردشده: {r['skipped']} | خطا: {r['failed']}")

        # ورد ساختار سازمانی
        if "word_structure" in found:
            path, root_name = found["word_structure"]
            print(f"\n      → در حال خواندن ورد: {path.name}")
            r = import_word(session, path, root_name=root_name)
            reports.append(r)
            session.commit()
            print(f"        واردشده: {r['imported']} | ردشده: {r['skipped']} | خطا: {r['failed']}")

        # ورد رفاهی
        if "word_welfare" in found:
            path, root_name = found["word_welfare"]
            print(f"\n      → در حال خواندن ورد: {path.name}")
            r = import_word(session, path, root_name=root_name)
            reports.append(r)
            session.commit()
            print(f"        واردشده: {r['imported']} | ردشده: {r['skipped']} | خطا: {r['failed']}")

        print()
        print("[4/4] گزارش نهایی...")
        final = generate_import_report(session)
        print(final)

    # خلاصه
    total_imported = sum(r.get("imported", 0) for r in reports)
    total_failed = sum(r.get("failed", 0) for r in reports)

    print()
    print("=" * 60)
    if total_failed == 0 and total_imported > 0:
        print(f"  ✅ موفقیت‌آمیز — {total_imported} پرسش‌وپاسخ وارد شد.")
        print("  حالا ربات را با  python app.py  اجرا کنید.")
    elif total_imported > 0:
        print(f"  ⚠ جزئی — {total_imported} وارد شد، {total_failed} خطا.")
    else:
        print("  ❌ واردسازی ناموفق بود.")
    print("=" * 60)


if __name__ == "__main__":
    main()
