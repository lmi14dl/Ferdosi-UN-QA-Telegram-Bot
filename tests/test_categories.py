"""تست دسته‌بندی‌ها"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from database.connection import init_db, get_session, engine, Base
from services.category_service import (
    get_or_create_category, get_children, create_category, delete_category, get_path
)


@pytest.fixture(scope="function")
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield


def test_hierarchy(setup_db):
    with get_session() as session:
        root = get_or_create_category(session, "ریشه")
        child = get_or_create_category(session, "فرزند", parent_id=root.id)
        children = get_children(session, root.id)
        assert len(children) == 1
        assert children[0].name == "فرزند"
        path = get_path(session, child.id)
        assert path == ["ریشه", "فرزند"]


def test_no_duplicate(setup_db):
    with get_session() as session:
        c1 = get_or_create_category(session, "یکتا")
        c2 = get_or_create_category(session, "یکتا")
        assert c1.id == c2.id


def test_delete_empty(setup_db):
    with get_session() as session:
        c = create_category(session, "حذف‌شدنی")
        ok = delete_category(session, c.id)
        assert ok is True
