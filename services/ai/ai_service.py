"""هماهنگ‌کننده فرایند RAG"""
from __future__ import annotations
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from database.models import Setting, Question
from services.ai.retriever import get_retriever, ensure_index, RetrievalResult
from services.ai.grounding import (
    decide_grounding,
    build_user_prompt,
    looks_like_injection,
    SYSTEM_PROMPT,
    DEFAULT_NO_INFO_MSG,
)
from services.ai.openrouter_provider import OpenRouterProvider
from services.ai.llm_provider import LLMProvider, LLMResponse
from config import (
    OPENROUTER_API_KEY,
    AI_MODEL,
    AI_ENABLED_DEFAULT,
    AI_SCORE_THRESHOLD,
    AI_TOP_K,
    AI_MAX_TOKENS,
    AI_RATE_LIMIT_PER_MINUTE,
)

logger = logging.getLogger(__name__)

# محدودیت نرخ در حافظه: user_id -> لیست timestamp
_rate_buckets: Dict[int, List[float]] = {}


@dataclass
class AIAnswer:
    text: str
    success: bool
    grounded: bool
    sources: str = ""
    error: Optional[str] = None
    used_llm: bool = False
    model: str = ""
    scores: List[float] = None


def _get_setting(session: Session, key: str, default: str = "") -> str:
    row = session.query(Setting).filter(Setting.key == key).first()
    return row.value if row else default


def _set_setting(session: Session, key: str, value: str):
    row = session.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = value
    else:
        session.add(Setting(key=key, value=value))
    session.flush()


def is_ai_enabled(session: Session) -> bool:
    val = _get_setting(session, "ai_enabled", "1" if AI_ENABLED_DEFAULT else "0")
    return val in ("1", "true", "True", "yes")


def set_ai_enabled(session: Session, enabled: bool):
    _set_setting(session, "ai_enabled", "1" if enabled else "0")


def get_score_threshold(session: Session) -> float:
    try:
        return float(_get_setting(session, "ai_score_threshold", str(AI_SCORE_THRESHOLD)))
    except ValueError:
        return AI_SCORE_THRESHOLD


def get_top_k(session: Session) -> int:
    try:
        return int(_get_setting(session, "ai_top_k", str(AI_TOP_K)))
    except ValueError:
        return AI_TOP_K


def get_no_info_message(session: Session) -> str:
    return _get_setting(session, "ai_no_info_msg", DEFAULT_NO_INFO_MSG) or DEFAULT_NO_INFO_MSG


def show_sources(session: Session) -> bool:
    return _get_setting(session, "ai_show_sources", "1") in ("1", "true", "True")


def check_rate_limit(user_id: int, limit: int = None) -> Tuple[bool, int]:
    """برمی‌گرداند (مجاز است؟, ثانیه تا آزاد شدن)"""
    limit = limit or AI_RATE_LIMIT_PER_MINUTE
    now = time.time()
    bucket = _rate_buckets.setdefault(user_id, [])
    # حذف قدیمی‌تر از ۶۰ ثانیه
    bucket[:] = [t for t in bucket if now - t < 60]
    if len(bucket) >= limit:
        wait = int(60 - (now - bucket[0])) + 1
        return False, max(wait, 1)
    bucket.append(now)
    return True, 0


def get_llm_provider(session: Session = None) -> LLMProvider:
    model = AI_MODEL
    if session:
        model = _get_setting(session, "ai_model", AI_MODEL) or AI_MODEL
    return OpenRouterProvider(api_key=OPENROUTER_API_KEY, model=model)


def answer_question(session: Session, user_id: int, question: str) -> AIAnswer:
    """
    جریان کامل RAG:
    rate limit → enable check → retrieve → ground → (optional) LLM
    """
    question = (question or "").strip()
    if not question:
        return AIAnswer(text="لطفاً سؤال خود را بنویسید.", success=False, grounded=False)

    if len(question) > 1500:
        return AIAnswer(
            text="سؤال بسیار طولانی است. لطفاً خلاصه‌تر بپرسید.",
            success=False,
            grounded=False,
        )

    if not is_ai_enabled(session):
        return AIAnswer(
            text="پاسخ‌گویی هوشمند در حال حاضر غیرفعال است. از منوی دسته‌بندی‌ها استفاده کنید.",
            success=False,
            grounded=False,
        )

    ok, wait = check_rate_limit(user_id)
    if not ok:
        return AIAnswer(
            text=f"تعداد درخواست‌های شما زیاد است. لطفاً حدود {wait} ثانیه صبر کنید.",
            success=False,
            grounded=False,
        )

    if looks_like_injection(question):
        logger.warning("Possible prompt injection from user %s", user_id)
        # همچنان بازیابی می‌کنیم اما مدل را با system قوی محدود می‌کنیم

    # ایندکس
    ensure_index(session)
    retriever = get_retriever()
    threshold = get_score_threshold(session)
    top_k = get_top_k(session)

    results = retriever.retrieve(question, top_k=top_k, min_hybrid_score=threshold * 0.4)
    decision = decide_grounding(results, score_threshold=threshold, max_chunks=top_k, query=question)

    no_info = get_no_info_message(session)

    if not decision.enough:
        logger.info(
            "Not grounded for user %s: %s | best=%s",
            user_id,
            decision.reason,
            results[0].score if results else None,
        )
        return AIAnswer(
            text=no_info,
            success=True,
            grounded=False,
            sources="",
            scores=[r.score for r in results[:3]] if results else [],
        )

    # فراخوانی مدل
    provider = get_llm_provider(session)
    if not provider.is_available():
        # بدون LLM: بهترین پاسخ ثبت‌شده را نمایش بده
        best = decision.results[0].chunk
        text = (
            f"{best.answer_text}\n\n"
            f"_(پاسخ مستقیم از پایگاه دانش — مدل زبانی در دسترس نیست)_"
        )
        sources = decision.sources_summary if show_sources(session) else ""
        return AIAnswer(
            text=text,
            success=True,
            grounded=True,
            sources=sources,
            used_llm=False,
            scores=[r.score for r in decision.results],
        )

    user_prompt = build_user_prompt(question, decision.context_text)
    llm_resp: LLMResponse = provider.generate(
        SYSTEM_PROMPT,
        user_prompt,
        max_tokens=AI_MAX_TOKENS,
        temperature=0.15,
    )

    if not llm_resp.success:
        # خطای API → بدون ساخت پاسخ جعلی
        best = decision.results[0].chunk
        fallback = (
            f"{best.answer_text}\n\n"
            f"⚠️ سرویس مدل موقتاً در دسترس نیست ({llm_resp.error}). "
            f"پاسخ بالا مستقیماً از منابع ثبت‌شده است."
        )
        return AIAnswer(
            text=fallback,
            success=True,
            grounded=True,
            sources=decision.sources_summary if show_sources(session) else "",
            error=llm_resp.error,
            used_llm=False,
            model=llm_resp.model,
            scores=[r.score for r in decision.results],
        )

    text = llm_resp.text
    # اگر مدل پیام عدم وجود اطلاعات داد
    sources = ""
    if show_sources(session) and "اطلاعات کافی" not in text:
        sources = decision.sources_summary

    return AIAnswer(
        text=text,
        success=True,
        grounded=True,
        sources=sources,
        used_llm=True,
        model=llm_resp.model,
        scores=[r.score for r in decision.results],
    )


def rebuild_ai_index(session: Session) -> int:
    return get_retriever().rebuild(session)


def get_ai_stats(session: Session) -> dict:
    ret = get_retriever()
    return {
        "enabled": is_ai_enabled(session),
        "chunks": ret.chunk_count if ret._built else 0,
        "threshold": get_score_threshold(session),
        "top_k": get_top_k(session),
        "model": _get_setting(session, "ai_model", AI_MODEL),
        "api_configured": bool(OPENROUTER_API_KEY),
    }
