"""تست جستجوی فارسی"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from database.connection import init_db, get_session, engine, Base
from services.question_service import create_question
from services.category_service import get_or_create_category
from services.search_service import search_questions
from utils.persian_text import normalize_persian


@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    with get_session() as session:
        cat = get_or_create_category(session, "تست")
        create_question(
            session,
            "آیا بیمه محدودیت سنی دارد؟",
            "خیر، پوشش بر اساس لیست است.",
            category_id=cat.id,
            keywords=["سن", "محدودیت"],
        )
        create_question(
            session,
            "والدین چگونه بیمه می‌شوند؟",
            "در صورت تحت تکفل بودن.",
            category_id=cat.id,
            keywords=["والدین"],
        )
    yield


def test_normalize():
    assert normalize_persian("يک") == "یک"
    assert normalize_persian("كتاب") == "کتاب"


def test_search_y_k(setup_db):
    with get_session() as session:
        # جستجو با ی عربی
        results = search_questions(session, "بيمه")
        assert len(results) >= 1
        results2 = search_questions(session, "بیمه")
        assert len(results2) >= 1


def test_search_in_answer(setup_db):
    with get_session() as session:
        results = search_questions(session, "تحت تکفل")
        assert len(results) >= 1
