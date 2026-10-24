"""سرویس مدیریت پرسش و پاسخ"""
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import Question, QuestionKeyword, Service
from utils.persian_text import normalize_for_search
import hashlib


def _make_hash(question: str, answer: str, source: str = "") -> str:
    raw = f"{normalize_for_search(question)}|{normalize_for_search(answer)}|{source}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_question(session: Session, q_id: int) -> Optional[Question]:
    return session.query(Question).filter(Question.id == q_id).first()


def get_questions_by_category(
    session: Session, category_id: int, active_only: bool = True
) -> List[Question]:
    q = session.query(Question).filter(Question.category_id == category_id)
    if active_only:
        q = q.filter(Question.is_active == True)
    return q.order_by(Question.sort_order, Question.id).all()


def get_questions_by_service(
    session: Session, service_id: int, active_only: bool = True
) -> List[Question]:
    q = session.query(Question).filter(Question.service_id == service_id)
    if active_only:
        q = q.filter(Question.is_active == True)
    return q.order_by(Question.sort_order, Question.id).all()


def create_question(
    session: Session,
    question_text: str,
    answer_text: str,
    category_id: int = None,
    service_id: int = None,
    keywords: List[str] = None,
    source_file: str = None,
    source_row: int = None,
    sort_order: int = 0,
) -> Question:
    h = _make_hash(question_text, answer_text, source_file or "")
    existing = session.query(Question).filter(Question.source_hash == h).first()
    if existing:
        return existing

    q = Question(
        question_text=question_text.strip(),
        answer_text=answer_text.strip(),
        category_id=category_id,
        service_id=service_id,
        source_file=source_file,
        source_row=source_row,
        source_hash=h,
        sort_order=sort_order,
    )
    session.add(q)
    session.flush()

    if keywords:
        for kw in keywords:
            kw = kw.strip()
            if kw:
                session.add(QuestionKeyword(question_id=q.id, keyword=kw))
        session.flush()
    return q


def update_question(session: Session, q_id: int, **kwargs) -> Optional[Question]:
    q = get_question(session, q_id)
    if not q:
        return None
    keywords = kwargs.pop("keywords", None)
    for k, v in kwargs.items():
        if hasattr(q, k) and k not in ("id", "created_at", "source_hash"):
            setattr(q, k, v)
    if keywords is not None:
        session.query(QuestionKeyword).filter(QuestionKeyword.question_id == q_id).delete()
        for kw in keywords:
            kw = kw.strip()
            if kw:
                session.add(QuestionKeyword(question_id=q_id, keyword=kw))
    session.flush()
    return q


def delete_question(session: Session, q_id: int) -> bool:
    q = get_question(session, q_id)
    if not q:
        return False
    session.delete(q)
    session.flush()
    return True


def increment_view(session: Session, q_id: int):
    q = get_question(session, q_id)
    if q:
        q.view_count = (q.view_count or 0) + 1
        session.flush()


def count_questions(session: Session, active_only: bool = False) -> int:
    q = session.query(Question)
    if active_only:
        q = q.filter(Question.is_active == True)
    return q.count()


def get_or_create_service(
    session: Session, title: str, category_id: int, source_file: str = None
) -> Service:
    existing = (
        session.query(Service)
        .filter(Service.title == title, Service.category_id == category_id)
        .first()
    )
    if existing:
        return existing
    s = Service(title=title.strip(), category_id=category_id, source_file=source_file)
    session.add(s)
    session.flush()
    return s
