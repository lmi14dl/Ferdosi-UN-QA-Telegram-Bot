"""سرویس سطح بالای واردسازی"""
from pathlib import Path
from sqlalchemy.orm import Session
from importers.excel_importer import import_excel
from importers.word_importer import import_word
from importers.validate_import import generate_import_report
from config import ATTACHMENTS_DIR
import logging

logger = logging.getLogger(__name__)


def run_full_import(session: Session) -> str:
    """اجرای کامل واردسازی سه فایل"""
    reports = []

    # ۱. بیمه تکمیلی
    excel_path = ATTACHMENTS_DIR / "ربات_تلگرامی_بیمه_تکمیلی_نهایی.xlsx"
    if excel_path.exists():
        logger.info("Importing Excel: %s", excel_path.name)
        r = import_excel(session, excel_path)
        reports.append(r)
        session.commit()
    else:
        logger.warning("Excel file not found: %s", excel_path)

    # ۲. ساختار سازمانی
    word1 = ATTACHMENTS_DIR / "ربات_تلگرامی_گروه_ساختار_سازمانی،_تامین_و_بکارگماری.docx"
    if word1.exists():
        logger.info("Importing Word: %s", word1.name)
        r = import_word(session, word1, root_name=None)  # سطوح خود فایل ریشه هستند
        reports.append(r)
        session.commit()
    else:
        logger.warning("Word file not found: %s", word1)

    # ۳. رفاهی
    word2 = ATTACHMENTS_DIR / "فرم_جمع_آوری_اطلاعات_ربات_تلگرامی_—_اداره_نگهداشت_و_امور_رفاه.docx"
    if word2.exists():
        logger.info("Importing Word: %s", word2.name)
        r = import_word(session, word2, root_name="امور رفاهی و نگهداشت")
        reports.append(r)
        session.commit()
    else:
        logger.warning("Word file not found: %s", word2)

    final = generate_import_report(session)
    logger.info("\n%s", final)
    return final
