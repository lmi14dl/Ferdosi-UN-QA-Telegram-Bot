"""تست واردسازی داده‌ها"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from database.connection import init_db, get_session, engine, Base
from services.import_service import run_full_import
from database.models import Category, Question, Service
from config import ATTACHMENTS_DIR


@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    # cleanup optional


def test_full_import(setup_db):
    with get_session() as session:
        report = run_full_import(session)

    with get_session() as session:
        q_count = session.query(Question).count()
        cat_count = session.query(Category).count()
        assert q_count >= 150, f"Expected >=150 questions, got {q_count}"
        assert cat_count >= 20, f"Expected >=20 categories, got {cat_count}"
        # بیمه تکمیلی باید وجود داشته باشد
        insurance = session.query(Category).filter(Category.name == "بیمه تکمیلی").first()
        assert insurance is not None
        # امور رفاهی
        welfare = session.query(Category).filter(Category.name.contains("رفاهی")).first()
        assert welfare is not None


def test_no_duplicate_on_reimport(setup_db):
    with get_session() as session:
        run_full_import(session)
        count1 = session.query(Question).count()
    with get_session() as session:
        run_full_import(session)
        count2 = session.query(Question).count()
    assert count1 == count2, "Re-import created duplicates"
