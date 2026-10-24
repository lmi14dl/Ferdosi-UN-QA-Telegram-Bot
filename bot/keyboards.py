"""کیبوردهای Inline و Reply"""
from telebot import types
from typing import List, Optional, Dict, Any, Tuple
from utils.persian_text import truncate
from utils.pagination import paginate
from config import ITEMS_PER_PAGE, CREATOR_ENABLED, CREATOR_BUTTON_TEXT


def main_menu_keyboard(categories: List[Dict[str, Any]]) -> types.InlineKeyboardMarkup:
    """categories: list of dicts with keys id, name"""
    kb = types.InlineKeyboardMarkup(row_width=1)
    for cat in categories:
        kb.add(
            types.InlineKeyboardButton(
                text=f"📂 {truncate(cat['name'], 50)}",
                callback_data=f"cat:{cat['id']}:1",
            )
        )
    kb.add(
        types.InlineKeyboardButton("🤖 پرسش از هوش مصنوعی", callback_data="ai_ask"),
    )
    kb.add(
        types.InlineKeyboardButton("🔍 جستجو", callback_data="search", style="primary"),
        types.InlineKeyboardButton("📖 راهنما", callback_data="help"),
        row_width=2
    )
    if CREATOR_ENABLED:
        kb.add(
            types.InlineKeyboardButton(
                CREATOR_BUTTON_TEXT or "👨‍💻 درباره سازنده",
                callback_data="about_creator",
            )
        )
    return kb


def ai_result_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🤖 سؤال جدید", callback_data="ai_ask"),
        types.InlineKeyboardButton("🏠 صفحه اصلی", callback_data="home"),
    )
    return kb


def category_keyboard(
    categories: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    services: List[Dict[str, Any]],
    current_id: Optional[int],
    page: int = 1,
    path_label: str = "",
    back_id: Optional[int] = None,
) -> types.InlineKeyboardMarkup:
    """
    همه لیست‌ها dict هستند: id, name/title/question_text
    current_id: شناسه دسته فعلی (برای صفحه‌بندی)
    back_id: شناسه والد برای دکمه بازگشت (None یا 0 = صفحه اصلی)
    """
    kb = types.InlineKeyboardMarkup(row_width=1)

    page_cats, cur_page, total_pages = paginate(categories, page, ITEMS_PER_PAGE)
    for cat in page_cats:
        kb.add(
            types.InlineKeyboardButton(
                text=f"📁 {truncate(cat['name'], 50)}",
                callback_data=f"cat:{cat['id']}:1",
            )
        )

    for svc in services[:ITEMS_PER_PAGE]:
        kb.add(
            types.InlineKeyboardButton(
                text=f"🏷️ {truncate(svc['title'], 50)}",
                callback_data=f"svc:{svc['id']}:1",
            )
        )

    page_qs, _, _ = paginate(questions, page, ITEMS_PER_PAGE)
    for q in page_qs:
        kb.add(
            types.InlineKeyboardButton(
                text=f"❓ {truncate(q['question_text'], 50)}",
                callback_data=f"q:{q['id']}",
            )
        )

    nav = []
    if cur_page > 1:
        nav.append(
            types.InlineKeyboardButton(
                "◀️ قبلی", callback_data=f"cat:{current_id or 0}:{cur_page - 1}"
            )
        )
    if cur_page < total_pages:
        nav.append(
            types.InlineKeyboardButton(
                "▶️ بعدی", callback_data=f"cat:{current_id or 0}:{cur_page + 1}"
            )
        )
    if nav:
        kb.row(*nav)

    # بازگشت به والد واقعی (نه خود دسته فعلی)
    if back_id is not None:
        kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data=f"back:{back_id}"))
    kb.add(types.InlineKeyboardButton("🏠 صفحه اصلی", callback_data="home"))
    return kb


def question_detail_keyboard(q_id: int, category_id: Optional[int]) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    if category_id:
        kb.add(
            types.InlineKeyboardButton(
                "🔙 بازگشت به دسته", callback_data=f"cat:{category_id}:1"
            )
        )
    kb.add(
        types.InlineKeyboardButton("🏠 صفحه اصلی", callback_data="home"),
        types.InlineKeyboardButton("🔍 جستجو", callback_data="search"),
    )
    return kb


def search_results_keyboard(
    results: List[Tuple[Dict[str, Any], float]], page: int = 1
) -> types.InlineKeyboardMarkup:
    """results: list of (question_dict, score)"""
    kb = types.InlineKeyboardMarkup(row_width=1)
    page_items, cur, total = paginate(results, page, ITEMS_PER_PAGE)
    for q, score in page_items:
        kb.add(
            types.InlineKeyboardButton(
                text=f"❓ {truncate(q['question_text'], 50)}",
                callback_data=f"q:{q['id']}",
            )
        )
    nav = []
    if cur > 1:
        nav.append(types.InlineKeyboardButton("◀️", callback_data=f"spage:{cur - 1}"))
    if cur < total:
        nav.append(types.InlineKeyboardButton("▶️", callback_data=f"spage:{cur + 1}"))
    if nav:
        kb.row(*nav)
    kb.add(types.InlineKeyboardButton("🏠 صفحه اصلی", callback_data="home"))
    return kb


def admin_main_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📂 دسته‌بندی‌ها", callback_data="adm:cats"),
        types.InlineKeyboardButton("❓ پرسش‌ها", callback_data="adm:qs"),
    )
    kb.add(
        types.InlineKeyboardButton("➕ افزودن دسته", callback_data="adm:addcat"),
        types.InlineKeyboardButton("➕ افزودن پرسش", callback_data="adm:addq"),
    )
    kb.add(
        types.InlineKeyboardButton("📊 گزارش", callback_data="adm:stats"),
        types.InlineKeyboardButton("👥 مدیران", callback_data="adm:admins"),
    )
    kb.add(
        types.InlineKeyboardButton("🤖 تنظیمات AI", callback_data="adm:ai"),
    )
    kb.add(types.InlineKeyboardButton("🔙 خروج از مدیریت", callback_data="home"))
    return kb


def confirm_keyboard(action: str, entity_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ تأیید", callback_data=f"confirm:{action}:{entity_id}"),
        types.InlineKeyboardButton("❌ لغو", callback_data="adm:menu"),
    )
    return kb


def cancel_reply_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("❌ لغو")
    return kb


def remove_keyboard() -> types.ReplyKeyboardRemove:
    return types.ReplyKeyboardRemove()