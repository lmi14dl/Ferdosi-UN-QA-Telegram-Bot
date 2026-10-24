"""هندلرهای پرسش از هوش مصنوعی (RAG)"""
import logging
from telebot import TeleBot, types
from database.connection import get_session
from services.ai.ai_service import answer_question, is_ai_enabled, get_ai_stats
from services.audit_service import log_activity
from bot.states import get_state, set_state, clear_state, UserState
from bot.keyboards import ai_result_keyboard, remove_keyboard, main_menu_keyboard
from services.category_service import get_root_categories
from utils.persian_text import split_long_message

logger = logging.getLogger(__name__)


def _cat_to_dict(c):
    return {"id": c.id, "name": c.name or ""}


def register_ai_handlers(bot: TeleBot):

    @bot.callback_query_handler(func=lambda c: c.data == "ai_ask")
    def cb_ai_ask(call: types.CallbackQuery):
        with get_session() as session:
            enabled = is_ai_enabled(session)
        if not enabled:
            bot.answer_callback_query(
                call.id,
                "پاسخ‌گویی هوشمند فعلاً غیرفعال است.",
                show_alert=True,
            )
            return
        set_state(call.from_user.id, UserState.AI_ASKING)
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "🤖 *پرسش از هوش مصنوعی*\n\n"
            "سؤال خود را به زبان طبیعی بنویسید.\n"
            "پاسخ فقط بر اساس منابع ثبت‌شده در ربات (بیمه تکمیلی، ساختار سازمانی، امور رفاهی) داده می‌شود.\n\n"
            "برای لغو: /cancel",
            parse_mode="Markdown",
            reply_markup=remove_keyboard(),
        )

    @bot.message_handler(func=lambda m: get_state(m.from_user.id).state == UserState.AI_ASKING)
    def handle_ai_question(message: types.Message):
        text = (message.text or "").strip()
        if not text or text.startswith("/"):
            if text in ("/cancel", "❌ لغو"):
                clear_state(message.from_user.id)
                bot.send_message(message.chat.id, "لغو شد.", reply_markup=remove_keyboard())
            return

        waiting = bot.send_message(
            message.chat.id,
            "⏳ در حال جست‌وجو در منابع و آماده‌سازی پاسخ...",
        )

        try:
            with get_session() as session:
                result = answer_question(session, message.from_user.id, text)
                log_activity(
                    session,
                    message.from_user.id,
                    "ai_question",
                    detail=text[:120],
                )
        except Exception as e:
            logger.exception("AI answer error")
            clear_state(message.from_user.id)
            bot.edit_message_text(
                "خطایی در پردازش رخ داد. لطفاً بعداً دوباره تلاش کنید یا از منوی دسته‌بندی استفاده کنید.",
                message.chat.id,
                waiting.message_id,
            )
            return

        clear_state(message.from_user.id)

        reply = result.text
        if result.sources:
            reply += f"\n\n📎 *منابع:*\n{result.sources}"

        parts = split_long_message(reply)
        try:
            bot.edit_message_text(
                parts[0],
                message.chat.id,
                waiting.message_id,
                parse_mode="Markdown",
                reply_markup=ai_result_keyboard() if len(parts) == 1 else None,
            )
        except Exception:
            bot.send_message(
                message.chat.id,
                parts[0],
                parse_mode="Markdown",
                reply_markup=ai_result_keyboard() if len(parts) == 1 else None,
            )
        for p in parts[1:]:
            bot.send_message(message.chat.id, p, parse_mode="Markdown")
        if len(parts) > 1:
            bot.send_message(
                message.chat.id,
                "⬆️ پایان پاسخ",
                reply_markup=ai_result_keyboard(),
            )
