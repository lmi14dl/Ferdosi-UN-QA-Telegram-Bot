"""تست کنترل دسترسی"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from database.connection import init_db, get_session, engine, Base
from database.models import Admin
from services.audit_service import is_admin, is_super_admin


@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    with get_session() as session:
        session.add(Admin(telegram_id=111, role="super"))
        session.add(Admin(telegram_id=222, role="content"))
        session.add(Admin(telegram_id=333, role="content", is_active=False))
    yield


def test_is_admin(setup_db):
    with get_session() as session:
        assert is_admin(session, 111) is True
        assert is_admin(session, 222) is True
        assert is_admin(session, 333) is False
        assert is_admin(session, 999) is False


def test_super_admin(setup_db):
    with get_session() as session:
        assert is_super_admin(session, 111) is True
        assert is_super_admin(session, 222) is False
