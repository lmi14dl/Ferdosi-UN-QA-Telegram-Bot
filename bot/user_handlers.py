"""هندلرهای بخش کاربری"""
import logging
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException
from database.connection import get_session
from services.category_service import (
    get_root_categories, get_children, get_category, get_path
)
from services.question_service import (
    get_questions_by_category, get_questions_by_service, get_question, increment_view
)
from services.search_service import search_questions, get_question_path
from services.audit_service import ensure_user, log_activity
from bot.keyboards import (
    main_menu_keyboard, category_keyboard, question_detail_keyboard,
    search_results_keyboard, remove_keyboard
)
from bot.states import get_state, set_state, clear_state, UserState
from utils.persian_text import split_long_message
from database.models import Service
from config import (
    CREATOR_ENABLED, CREATOR_NAME, CREATOR_TELEGRAM_ID,
    CREATOR_USERNAME, CREATOR_TITLE, CREATOR_BIO,
)


logger = logging.getLogger(__name__)


def _cat_to_dict(c):
    return {"id": c.id, "name": c.name or ""}


def _q_to_dict(q):
    return {"id": q.id, "question_text": q.question_text or "", "category_id": q.category_id}


def _svc_to_dict(s):
    return {"id": s.id, "title": s.title or ""}


def _safe_edit_message(bot: TeleBot, text: str, chat_id, message_id, reply_markup=None, parse_mode=None):
    """ویرایش پیام؛ خطای message is not modified را نادیده می‌گیرد."""
    try:
        bot.edit_message_text(
            text,
            chat_id,
            message_id,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except ApiTelegramException as e:
        if "message is not modified" in str(e):
            logger.debug("message not modified (ignored)")
        else:
            raise


def register_user_handlers(bot: TeleBot):

    @bot.message_handler(commands=["start", "menu"])
    def cmd_start(message: types.Message):
        clear_state(message.from_user.id)
        with get_session() as session:
            ensure_user(
                session,
                message.from_user.id,
                message.from_user.username,
                message.from_user.full_name,
            )
            log_activity(session, message.from_user.id, "start")
            roots = [_cat_to_dict(c) for c in get_root_categories(session, active_only=True)]

        text = (
            "سلام 👋\n\n"
            "به ربات پرسش‌وپاسخ سازمانی دانشگاه فردوسی مشهد خوش آمدید.\n"
            "از منوی زیر حوزه موردنظر خود را انتخاب کنید یا جستجو نمایید."
        )
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=main_menu_keyboard(roots),
        )

    @bot.message_handler(commands=["help"])
    def cmd_help(message: types.Message):
        text = (
            "📖 *راهنمای استفاده*\n\n"
            "• از دکمه‌های منو برای پیمایش دسته‌بندی‌ها استفاده کنید.\n"
            "• با دکمه 🔍 جستجو می‌توانید مستقیماً سؤال خود را پیدا کنید.\n"
            "• در هر مرحله دکمه «بازگشت» و «صفحه اصلی» در دسترس است.\n"
            "• برای ارتباط با واحدها از اطلاعات تماس داخل پاسخ‌ها استفاده کنید.\n\n"
            "دستورات:\n"
            "/start - منوی اصلی\n"
            "/help - این راهنما\n"
            "/search - شروع جستجو"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    @bot.message_handler(commands=["search"])
    def cmd_search(message: types.Message):
        set_state(message.from_user.id, UserState.SEARCHING)
        bot.send_message(
            message.chat.id,
            "🔍 عبارت موردنظر خود را بنویسید:\n(یا /cancel برای لغو)",
            reply_markup=remove_keyboard(),
        )

    @bot.message_handler(commands=["cancel"])
    def cmd_cancel(message: types.Message):
        clear_state(message.from_user.id)
        bot.send_message(message.chat.id, "عملیات لغو شد.", reply_markup=remove_keyboard())
        cmd_start(message)

    @bot.callback_query_handler(func=lambda c: c.data == "home")
    def cb_home(call: types.CallbackQuery):
        clear_state(call.from_user.id)
        with get_session() as session:
            roots = [_cat_to_dict(c) for c in get_root_categories(session, active_only=True)]
        _safe_edit_message(
            bot,
            "🏠 صفحه اصلی\nحوزه موردنظر را انتخاب کنید:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu_keyboard(roots),
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data == "help")
    def cb_help(call: types.CallbackQuery):
        bot.answer_callback_query(call.id)
        cmd_help(call.message)

    @bot.callback_query_handler(func=lambda c: c.data == "search")
    def cb_search(call: types.CallbackQuery):
        set_state(call.from_user.id, UserState.SEARCHING)
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "🔍 عبارت موردنظر خود را بنویسید:\n(یا /cancel برای لغو)",
        )

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("cat:"))
    def cb_category(call: types.CallbackQuery):
        parts = call.data.split(":")
        cat_id = int(parts[1])
        page = int(parts[2]) if len(parts) > 2 else 1

        with get_session() as session:
            if cat_id == 0:
                roots = [_cat_to_dict(c) for c in get_root_categories(session, active_only=True)]
                _safe_edit_message(
                    bot,
                    "🏠 صفحه اصلی\nحوزه موردنظر را انتخاب کنید:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=main_menu_keyboard(roots),
                )
                bot.answer_callback_query(call.id)
                return

            cat = get_category(session, cat_id)
            if not cat or not cat.is_active:
                bot.answer_callback_query(call.id, "دسته‌بندی یافت نشد یا غیرفعال است.", show_alert=True)
                return

            # والد واقعی برای دکمه بازگشت (0 = صفحه اصلی)
            back_id = cat.parent_id if cat.parent_id else 0

            children = [_cat_to_dict(c) for c in get_children(session, cat_id, active_only=True)]
            questions = [_q_to_dict(q) for q in get_questions_by_category(session, cat_id, active_only=True)]
            services = [
                _svc_to_dict(s)
                for s in session.query(Service)
                .filter(Service.category_id == cat_id, Service.is_active == True)
                .order_by(Service.sort_order)
                .all()
            ]
            path = " › ".join(get_path(session, cat_id))

            text = f"📂 *{path}*\n\n"
            if not children and not questions and not services:
                text += "در حال حاضر محتوایی در این بخش ثبت نشده است."
            else:
                text += "زیرمجموعه یا پرسش موردنظر را انتخاب کنید:"

            kb = category_keyboard(
                children, questions, services,
                current_id=cat_id,
                page=page,
                path_label=path,
                back_id=back_id,
            )

        _safe_edit_message(
            bot,
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb,
            parse_mode="Markdown",
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("svc:"))
    def cb_service(call: types.CallbackQuery):
        parts = call.data.split(":")
        svc_id = int(parts[1])
        page = int(parts[2]) if len(parts) > 2 else 1

        with get_session() as session:
            svc = session.query(Service).filter(Service.id == svc_id).first()
            if not svc or not svc.is_active:
                bot.answer_callback_query(call.id, "خدمت یافت نشد.", show_alert=True)
                return
            svc_title = svc.title
            cat_id = svc.category_id
            questions = [_q_to_dict(q) for q in get_questions_by_service(session, svc_id, active_only=True)]
            text = f"🏷️ *{svc_title}*\n\nپرسش موردنظر را انتخاب کنید:"
            # بازگشت از خدمت → به دسته والد خدمت
            kb = category_keyboard(
                [], questions, [],
                current_id=cat_id,
                page=page,
                back_id=cat_id,
            )

        _safe_edit_message(
            bot,
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb,
            parse_mode="Markdown",
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("q:"))
    def cb_question(call: types.CallbackQuery):
        q_id = int(call.data.split(":")[1])
        with get_session() as session:
            q = get_question(session, q_id)
            if not q or not q.is_active:
                bot.answer_callback_query(call.id, "پرسش یافت نشد.", show_alert=True)
                return
            increment_view(session, q_id)
            log_activity(session, call.from_user.id, "view_question", target_id=q_id)
            path = get_question_path(session, q)
            q_text = q.question_text or ""
            answer = q.answer_text or "پاسخی ثبت نشده است."
            cat_id = q.category_id
            header = f"❓ *{q_text}*\n\n📍 {path}\n\n"
            full = header + answer
            parts = split_long_message(full)
            kb = question_detail_keyboard(q_id, cat_id)

        bot.answer_callback_query(call.id)
        _safe_edit_message(
            bot,
            parts[0],
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb if len(parts) == 1 else None,
            parse_mode="Markdown",
        )
        for part in parts[1:]:
            bot.send_message(call.message.chat.id, part, parse_mode="Markdown")
        if len(parts) > 1:
            bot.send_message(
                call.message.chat.id,
                "⬆️ پایان پاسخ",
                reply_markup=kb,
            )

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("back:"))
    def cb_back(call: types.CallbackQuery):
        # back_id از قبل والد واقعی است (نه دسته فعلی)
        parent_id = int(call.data.split(":")[1])
        call.data = f"cat:{parent_id}:1"
        cb_category(call)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("spage:"))
    def cb_search_page(call: types.CallbackQuery):
        page = int(call.data.split(":")[1])
        state = get_state(call.from_user.id)
        results = state.data.get("search_results", [])
        if not results:
            bot.answer_callback_query(call.id, "نتیجه‌ای موجود نیست.")
            return
        kb = search_results_keyboard(results, page)
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=kb
        )
        bot.answer_callback_query(call.id)

    
    @bot.callback_query_handler(func=lambda c: c.data == "about_creator")
    def cb_about_creator(call: types.CallbackQuery):
        """صفحه معرفی سازنده — بدون Markdown تا خطای parse ندهد"""
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass

        if not CREATOR_ENABLED:
            try:
                bot.answer_callback_query(call.id, "این بخش غیرفعال است.", show_alert=True)
            except Exception:
                pass
            return

        name = (CREATOR_NAME or "—").strip()
        title = (CREATOR_TITLE or "توسعه‌دهنده ربات").strip()
        tid = (CREATOR_TELEGRAM_ID or "").strip()
        uname = (CREATOR_USERNAME or "").strip().lstrip("@")
        bio = (CREATOR_BIO or "").strip()

        lines = [
            "👨‍💻 درباره سازنده ربات",
            "────────────────────",
            "",
            f"🏷 سمت: {title}",
        ]
        if tid:
            lines.append(f"🆔 شناسه تلگرام: {tid}")
        if uname:
            lines.append(f"🔗 نام کاربری: @{uname}")
        if bio:
            lines.extend(["", f"📝 {bio}"])
        lines.extend(["", "با احترام"])

        text = "\n".join(lines)

        kb = types.InlineKeyboardMarkup(row_width=1)
        if uname:
            kb.add(
                types.InlineKeyboardButton(
                    f"💬 پیام به @{uname}",
                    url=f"https://t.me/{uname}",
                )
            )
        kb.add(types.InlineKeyboardButton("🏠 صفحه اصلی", callback_data="home"))

        try:
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=kb,
            )
        except Exception as e:
            logger.warning("about_creator edit failed: %s", e)
            try:
                bot.send_message(
                    call.message.chat.id,
                    text,
                    reply_markup=kb,
                )
            except Exception as e2:
                logger.exception("about_creator send failed: %s", e2)


    @bot.message_handler(func=lambda m: get_state(m.from_user.id).state == UserState.SEARCHING)
    def handle_search_query(message: types.Message):
        query = (message.text or "").strip()
        if not query or query.startswith("/"):
            return
        with get_session() as session:
            raw_results = search_questions(session, query, limit=30)
            # تبدیل به dict قبل از بستن session
            results = [(_q_to_dict(q), score) for q, score in raw_results]
            log_activity(session, message.from_user.id, "search", detail=query[:100])

        clear_state(message.from_user.id)
        if not results:
            bot.send_message(
                message.chat.id,
                "نتیجه‌ای یافت نشد. 😕\nعبارت دیگری امتحان کنید یا از منوی اصلی استفاده کنید.",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🏠 صفحه اصلی", callback_data="home"),
                    types.InlineKeyboardButton("🔍 جستجوی مجدد", callback_data="search"),
                ),
            )
            return

        set_state(message.from_user.id, UserState.IDLE, search_results=results)
        text = f"🔍 *نتایج جستجو برای:* `{query}`\nتعداد: {len(results)}\n\nیکی را انتخاب کنید:"
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=search_results_keyboard(results, 1),
            parse_mode="Markdown",
        )