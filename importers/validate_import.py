"""اعتبارسنجی و گزارش نهایی واردسازی"""
from sqlalchemy.orm import Session
from database.models import Category, Question, Service, ImportJob, ContactPoint


def generate_import_report(session: Session) -> str:
    lines = ["=" * 50, "گزارش نهایی واردسازی داده‌ها", "=" * 50, ""]

    jobs = session.query(ImportJob).order_by(ImportJob.id).all()
    for j in jobs:
        lines.append(f"📁 فایل: {j.source_file}")
        lines.append(f"   وضعیت: {j.status}")
        lines.append(f"   کل ردیف: {j.total_rows} | واردشده: {j.imported} | ردشده: {j.skipped} | خطا: {j.failed}")
        lines.append(f"   جزئیات: {j.report}")
        lines.append("")

    lines.append("-" * 40)
    lines.append(f"تعداد دسته‌بندی‌ها: {session.query(Category).count()}")
    lines.append(f"تعداد خدمات: {session.query(Service).count()}")
    lines.append(f"تعداد پرسش‌وپاسخ: {session.query(Question).count()}")
    lines.append(f"تعداد نقاط تماس: {session.query(ContactPoint).count()}")
    lines.append("")

    # ریشه دسته‌ها
    roots = session.query(Category).filter(Category.parent_id.is_(None)).all()
    lines.append("دسته‌بندی‌های ریشه:")
    for r in roots:
        child_count = session.query(Category).filter(Category.parent_id == r.id).count()
        q_count = session.query(Question).filter(Question.category_id == r.id).count()
        lines.append(f"  • {r.name} (زیرمجموعه: {child_count}, پرسش مستقیم: {q_count})")

    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)
