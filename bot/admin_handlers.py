"""هندلرهای پنل مدیریت"""
import logging
from telebot import TeleBot, types
from database.connection import get_session
from database.models import Admin, Category, Question, Service
from services.category_service import (
    get_root_categories, get_children, get_category, create_category,
    update_category, delete_category, count_categories
)
from services.question_service import (
    create_question, update_question, delete_question, get_question, count_questions
)
from services.audit_service import is_admin, is_super_admin, get_admin, log_audit, ensure_user
from bot.keyboards import admin_main_keyboard, confirm_keyboard, cancel_reply_keyboard, remove_keyboard
from bot.states import get_state, set_state, clear_state, UserState, update_data
from config import INITIAL_ADMIN_IDS
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _check_admin(bot: TeleBot, message_or_call) -> bool:
    uid = message_or_call.from_user.id
    with get_session() as session:
        if is_admin(session, uid):
            return True
        # bootstrap initial admins
        if uid in INITIAL_ADMIN_IDS:
            existing = session.query(Admin).filter(Admin.telegram_id == uid).first()
            if not existing:
                session.add(Admin(telegram_id=uid, role="super", full_name=message_or_call.from_user.full_name or ""))
                session.flush()
            return True
    return False


def register_admin_handlers(bot: TeleBot):

    @bot.message_handler(commands=["admin"])
    def cmd_admin(message: types.Message):
        if not _check_admin(bot, message):
            bot.reply_to(message, "⛔️ شما دسترسی مدیریت ندارید.")
            return
        clear_state(message.from_user.id)
        set_state(message.from_user.id, UserState.ADMIN_MENU)
        bot.send_message(
            message.chat.id,
            "🔐 *پنل مدیریت*\nعملیات موردنظر را انتخاب کنید:",
            reply_markup=admin_main_keyboard(),
            parse_mode="Markdown",
        )

    @bot.callback_query_handler(func=lambda c: c.data == "adm:menu")
    def cb_admin_menu(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            bot.answer_callback_query(call.id, "دسترسی ندارید", show_alert=True)
            return
        clear_state(call.from_user.id)
        bot.edit_message_text(
            "🔐 پنل مدیریت",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=admin_main_keyboard(),
        )
        bot.answer_callback_query(call.id)

    # ---------- آمار ----------
    @bot.callback_query_handler(func=lambda c: c.data == "adm:stats")
    def cb_stats(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        with get_session() as session:
            from database.models import User, UserActivity, ImportJob
            text = (
                "📊 *گزارش سامانه*\n\n"
                f"• دسته‌بندی‌ها: {count_categories(session)}\n"
                f"• پرسش‌وپاسخ فعال: {count_questions(session, active_only=True)}\n"
                f"• کل پرسش‌ها: {count_questions(session)}\n"
                f"• کاربران یکتا: {session.query(User).count()}\n"
                f"• فعالیت‌ها: {session.query(UserActivity).count()}\n"
                f"• مدیران: {session.query(Admin).filter(Admin.is_active==True).count()}\n"
            )
            jobs = session.query(ImportJob).order_by(ImportJob.id.desc()).limit(3).all()
            if jobs:
                text += "\n*آخرین واردسازی‌ها:*\n"
                for j in jobs:
                    text += f"  – {j.source_file}: {j.status} ({j.imported}/{j.total_rows})\n"
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm:menu")
            ),
            parse_mode="Markdown",
        )
        bot.answer_callback_query(call.id)

    # ---------- لیست دسته‌ها ----------
    @bot.callback_query_handler(func=lambda c: c.data == "adm:cats")
    def cb_list_cats(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        with get_session() as session:
            roots = get_root_categories(session, active_only=False)
            text = "📂 *دسته‌بندی‌های ریشه:*\n\n"
            kb = types.InlineKeyboardMarkup(row_width=1)
            for c in roots:
                status = "✅" if c.is_active else "❌"
                text += f"{status} `{c.id}` – {c.name}\n"
                kb.add(types.InlineKeyboardButton(
                    f"{status} {c.name[:40]}",
                    callback_data=f"adm:cat:{c.id}"
                ))
            kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm:menu"))
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            reply_markup=kb, parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm:cat:"))
    def cb_cat_detail(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        cat_id = int(call.data.split(":")[2])
        with get_session() as session:
            cat = get_category(session, cat_id)
            if not cat:
                bot.answer_callback_query(call.id, "یافت نشد")
                return
            children = get_children(session, cat_id, active_only=False)
            q_count = session.query(Question).filter(Question.category_id == cat_id).count()
            text = (
                f"📂 *{cat.name}*\n"
                f"شناسه: `{cat.id}`\n"
                f"وضعیت: {'فعال' if cat.is_active else 'غیرفعال'}\n"
                f"زیرمجموعه: {len(children)}\n"
                f"پرسش: {q_count}\n"
            )
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton(
                    "✏️ ویرایش نام", callback_data=f"adm:editcat:{cat_id}"
                ),
                types.InlineKeyboardButton(
                    "🔄 فعال/غیرفعال", callback_data=f"adm:togglecat:{cat_id}"
                ),
            )
            kb.add(
                types.InlineKeyboardButton(
                    "🗑 حذف", callback_data=f"adm:delcat:{cat_id}"
                ),
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm:cats"),
            )
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            reply_markup=kb, parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm:togglecat:"))
    def cb_toggle_cat(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        cat_id = int(call.data.split(":")[2])
        with get_session() as session:
            cat = get_category(session, cat_id)
            if cat:
                cat.is_active = not cat.is_active
                log_audit(session, call.from_user.id, "toggle_category", "category", cat_id, str(cat.is_active))
                session.flush()
        bot.answer_callback_query(call.id, "وضعیت تغییر کرد")
        call.data = f"adm:cat:{cat_id}"
        cb_cat_detail(call)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("adm:delcat:"))
    def cb_del_cat(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        cat_id = int(call.data.split(":")[2])
        bot.edit_message_text(
            f"⚠️ آیا از حذف دسته‌بندی `{cat_id}` مطمئن هستید؟\n(در صورت داشتن محتوا حذف انجام نمی‌شود)",
            call.message.chat.id, call.message.message_id,
            reply_markup=confirm_keyboard("delcat", cat_id),
            parse_mode="Markdown",
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("confirm:delcat:"))
    def cb_confirm_del_cat(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        cat_id = int(call.data.split(":")[2])
        with get_session() as session:
            ok = delete_category(session, cat_id, cascade=False)
            if ok:
                log_audit(session, call.from_user.id, "delete_category", "category", cat_id)
                msg = "✅ حذف شد."
            else:
                msg = "❌ حذف نشد (احتمالاً دارای زیرمجموعه یا پرسش است)."
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(
                                  types.InlineKeyboardButton("🔙", callback_data="adm:cats")
                              ))
        bot.answer_callback_query(call.id)

    # ---------- افزودن دسته ----------
    @bot.callback_query_handler(func=lambda c: c.data == "adm:addcat")
    def cb_add_cat(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        set_state(call.from_user.id, UserState.ADMIN_ADD_CAT_NAME)
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "نام دسته‌بندی جدید را بنویسید:\n(/cancel برای لغو)",
            reply_markup=cancel_reply_keyboard(),
        )

    @bot.message_handler(func=lambda m: get_state(m.from_user.id).state == UserState.ADMIN_ADD_CAT_NAME)
    def handle_add_cat_name(message: types.Message):
        if not _check_admin(bot, message):
            return
        name = (message.text or "").strip()
        if name in ("❌ لغو", "/cancel"):
            clear_state(message.from_user.id)
            bot.send_message(message.chat.id, "لغو شد.", reply_markup=remove_keyboard())
            return
        if not name:
            bot.reply_to(message, "نام معتبر وارد کنید.")
            return
        with get_session() as session:
            cat = create_category(session, name)
            log_audit(session, message.from_user.id, "create_category", "category", cat.id, name)
        clear_state(message.from_user.id)
        bot.send_message(
            message.chat.id,
            f"✅ دسته‌بندی «{name}» با شناسه `{cat.id}` ایجاد شد.",
            reply_markup=remove_keyboard(),
            parse_mode="Markdown",
        )
        bot.send_message(message.chat.id, "پنل مدیریت:", reply_markup=admin_main_keyboard())

    # ---------- افزودن پرسش ----------
    @bot.callback_query_handler(func=lambda c: c.data == "adm:addq")
    def cb_add_q(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        set_state(call.from_user.id, UserState.ADMIN_ADD_Q_TEXT)
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "متن پرسش را بنویسید:\n(/cancel برای لغو)",
            reply_markup=cancel_reply_keyboard(),
        )

    @bot.message_handler(func=lambda m: get_state(m.from_user.id).state == UserState.ADMIN_ADD_Q_TEXT)
    def handle_add_q_text(message: types.Message):
        if not _check_admin(bot, message):
            return
        text = (message.text or "").strip()
        if text in ("❌ لغو", "/cancel"):
            clear_state(message.from_user.id)
            bot.send_message(message.chat.id, "لغو شد.", reply_markup=remove_keyboard())
            return
        update_data(message.from_user.id, question_text=text)
        set_state(message.from_user.id, UserState.ADMIN_ADD_Q_ANSWER)
        bot.send_message(message.chat.id, "حالا متن پاسخ را بنویسید:")

    @bot.message_handler(func=lambda m: get_state(m.from_user.id).state == UserState.ADMIN_ADD_Q_ANSWER)
    def handle_add_q_answer(message: types.Message):
        if not _check_admin(bot, message):
            return
        answer = (message.text or "").strip()
        if answer in ("❌ لغو", "/cancel"):
            clear_state(message.from_user.id)
            bot.send_message(message.chat.id, "لغو شد.", reply_markup=remove_keyboard())
            return
        state = get_state(message.from_user.id)
        q_text = state.data.get("question_text", "")
        with get_session() as session:
            # به اولین ریشه وصل می‌شود؛ مدیر بعداً می‌تواند جابه‌جا کند
            roots = get_root_categories(session, active_only=False)
            cat_id = roots[0].id if roots else None
            q = create_question(session, q_text, answer, category_id=cat_id)
            log_audit(session, message.from_user.id, "create_question", "question", q.id)
        clear_state(message.from_user.id)
        bot.send_message(
            message.chat.id,
            f"✅ پرسش با شناسه `{q.id}` ثبت شد.",
            reply_markup=remove_keyboard(),
            parse_mode="Markdown",
        )
        bot.send_message(message.chat.id, "پنل مدیریت:", reply_markup=admin_main_keyboard())

    # ---------- لیست پرسش‌ها (خلاصه) ----------
    @bot.callback_query_handler(func=lambda c: c.data == "adm:qs")
    def cb_list_qs(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        with get_session() as session:
            total = count_questions(session)
            recent = (
                session.query(Question)
                .order_by(Question.id.desc())
                .limit(10)
                .all()
            )
            text = f"❓ *آخرین پرسش‌ها* (کل: {total})\n\n"
            for q in recent:
                status = "✅" if q.is_active else "❌"
                text += f"{status} `{q.id}` {q.question_text[:50]}…\n"
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm:menu"))
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            reply_markup=kb, parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    # ---------- مدیران ----------
    @bot.callback_query_handler(func=lambda c: c.data == "adm:admins")
    def cb_admins(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        with get_session() as session:
            if not is_super_admin(session, call.from_user.id) and call.from_user.id not in INITIAL_ADMIN_IDS:
                bot.answer_callback_query(call.id, "فقط مدیرکل می‌تواند مدیران را ببیند", show_alert=True)
                return
            admins = session.query(Admin).filter(Admin.is_active == True).all()
            text = "👥 *مدیران فعال:*\n\n"
            for a in admins:
                text += f"• `{a.telegram_id}` – {a.role} – {a.full_name or '—'}\n"
            kb = types.InlineKeyboardMarkup(row_width=1)
            kb.add(types.InlineKeyboardButton("➕ افزودن مدیر", callback_data="adm:addadmin"))
            kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm:menu"))
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            reply_markup=kb, parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == "adm:addadmin")
    def cb_add_admin(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        set_state(call.from_user.id, UserState.ADMIN_ADD_ADMIN_ID)
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "شناسه عددی تلگرام مدیر جدید را ارسال کنید:\n(/cancel برای لغو)",
            reply_markup=cancel_reply_keyboard(),
        )

    @bot.message_handler(func=lambda m: get_state(m.from_user.id).state == UserState.ADMIN_ADD_ADMIN_ID)
    def handle_add_admin(message: types.Message):
        if not _check_admin(bot, message):
            return
        text = (message.text or "").strip()
        if text in ("❌ لغو", "/cancel"):
            clear_state(message.from_user.id)
            bot.send_message(message.chat.id, "لغو شد.", reply_markup=remove_keyboard())
            return
        if not text.isdigit():
            bot.reply_to(message, "شناسه باید عدد باشد.")
            return
        tid = int(text)
        with get_session() as session:
            if not is_super_admin(session, message.from_user.id) and message.from_user.id not in INITIAL_ADMIN_IDS:
                bot.reply_to(message, "دسترسی ندارید.")
                clear_state(message.from_user.id)
                return
            existing = session.query(Admin).filter(Admin.telegram_id == tid).first()
            if existing:
                existing.is_active = True
                msg = "مدیر قبلی دوباره فعال شد."
            else:
                session.add(Admin(telegram_id=tid, role="content", created_by=message.from_user.id))
                msg = "✅ مدیر جدید اضافه شد."
            log_audit(session, message.from_user.id, "add_admin", "admin", tid)
        clear_state(message.from_user.id)
        bot.send_message(message.chat.id, msg, reply_markup=remove_keyboard())
        bot.send_message(message.chat.id, "پنل مدیریت:", reply_markup=admin_main_keyboard())


    # ---------- تنظیمات AI ----------
    @bot.callback_query_handler(func=lambda c: c.data == "adm:ai")
    def cb_ai_settings(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        from services.ai.ai_service import get_ai_stats, is_ai_enabled
        with get_session() as session:
            stats = get_ai_stats(session)
        status = "✅ فعال" if stats["enabled"] else "❌ غیرفعال"
        api = "✅ تنظیم شده" if stats["api_configured"] else "⚠️ بدون API Key"
        text = (
            "🤖 *تنظیمات هوش مصنوعی*\n\n"
            f"وضعیت: {status}\n"
            f"تعداد بخش‌های دانش: {stats['chunks']}\n"
            f"آستانه ارتباط: {stats['threshold']}\n"
            f"تعداد منابع بازیابی: {stats['top_k']}\n"
            f"مدل: `{stats['model']}`\n"
            f"API: {api}\n"
        )
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton(
                "🔄 فعال/غیرفعال کردن AI",
                callback_data="adm:ai_toggle",
            ),
            types.InlineKeyboardButton(
                "📚 بازسازی نمایه جست‌وجو",
                callback_data="adm:ai_reindex",
            ),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm:menu"),
        )
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb,
            parse_mode="Markdown",
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == "adm:ai_toggle")
    def cb_ai_toggle(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        from services.ai.ai_service import is_ai_enabled, set_ai_enabled
        with get_session() as session:
            new_val = not is_ai_enabled(session)
            set_ai_enabled(session, new_val)
            log_audit(session, call.from_user.id, "ai_toggle", detail=str(new_val))
        bot.answer_callback_query(call.id, "وضعیت AI تغییر کرد")
        call.data = "adm:ai"
        cb_ai_settings(call)

    @bot.callback_query_handler(func=lambda c: c.data == "adm:ai_reindex")
    def cb_ai_reindex(call: types.CallbackQuery):
        if not _check_admin(bot, call):
            return
        from services.ai.ai_service import rebuild_ai_index
        bot.answer_callback_query(call.id, "در حال بازسازی...")
        with get_session() as session:
            n = rebuild_ai_index(session)
            log_audit(session, call.from_user.id, "ai_reindex", detail=str(n))
        bot.edit_message_text(
            f"✅ نمایه بازسازی شد. تعداد بخش‌ها: {n}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm:ai")
            ),
        )
