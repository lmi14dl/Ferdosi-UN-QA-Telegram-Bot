"""سرویس جستجوی فارسی"""
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database.models import Question, QuestionKeyword, Category, Service
from utils.persian_text import normalize_for_search, normalize_persian


def search_questions(
    session: Session, query: str, limit: int = 20, active_only: bool = True
) -> List[Tuple[Question, float]]:
    """
    جستجو در پرسش، پاسخ، کلمات کلیدی، عنوان خدمت و نام دسته‌بندی.
    برمی‌گرداند لیست (Question, score)
    """
    if not query or not query.strip():
        return []

    norm_q = normalize_for_search(query)
    tokens = [t for t in norm_q.split() if len(t) >= 2]
    if not tokens:
        tokens = [norm_q]

    # دریافت همه سوالات فعال
    q = session.query(Question)
    if active_only:
        q = q.filter(Question.is_active == True)
    questions = q.all()

    results = []
    for question in questions:
        score = _score_question(question, tokens, norm_q)
        if score > 0:
            results.append((question, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]


def _score_question(question: Question, tokens: List[str], full_query: str) -> float:
    score = 0.0
    q_text = normalize_for_search(question.question_text or "")
    a_text = normalize_for_search(question.answer_text or "")
    kw_text = " ".join(
        normalize_for_search(k.keyword) for k in (question.keywords or [])
    )

    # تطابق کامل عبارت
    if full_query in q_text:
        score += 50
    if full_query in a_text:
        score += 20
    if full_query in kw_text:
        score += 30

    for token in tokens:
        if token in q_text:
            score += 10
        if token in a_text:
            score += 3
        if token in kw_text:
            score += 8

        # عنوان خدمت و دسته‌بندی
        if question.service and token in normalize_for_search(question.service.title):
            score += 5
        if question.category and token in normalize_for_search(question.category.name):
            score += 4

    return score


def get_question_path(session: Session, question: Question) -> str:
    """مسیر خوانا برای نمایش نتیجه جستجو"""
    parts = []
    if question.category:
        from services.category_service import get_path
        parts = get_path(session, question.category_id)
    if question.service:
        parts.append(question.service.title)
    return " › ".join(parts) if parts else "—"
