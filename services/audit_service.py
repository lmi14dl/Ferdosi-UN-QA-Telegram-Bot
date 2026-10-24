"""ثبت رخدادهای مدیریتی و فعالیت کاربران"""
from sqlalchemy.orm import Session
from database.models import AuditLog, User, UserActivity, Admin
from datetime import datetime, timezone


def log_audit(
    session: Session,
    admin_telegram_id: int,
    action: str,
    entity_type: str = None,
    entity_id: int = None,
    detail: str = "",
):
    entry = AuditLog(
        admin_telegram_id=admin_telegram_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail[:2000] if detail else "",
    )
    session.add(entry)
    session.flush()


def ensure_user(session: Session, telegram_id: int, username: str = None, full_name: str = None) -> User:
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        user.last_seen = datetime.now(timezone.utc)
        user.activity_count = (user.activity_count or 0) + 1
        if username:
            user.username = username
        if full_name:
            user.full_name = full_name
    else:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
        )
        session.add(user)
    session.flush()
    return user


def log_activity(
    session: Session,
    telegram_id: int,
    action: str,
    target_id: int = None,
    detail: str = "",
    user_id: int = None,
):
    entry = UserActivity(
        user_id=user_id,
        telegram_id=telegram_id,
        action=action,
        target_id=target_id,
        detail=detail[:250],
    )
    session.add(entry)
    session.flush()


def is_admin(session: Session, telegram_id: int) -> bool:
    admin = (
        session.query(Admin)
        .filter(Admin.telegram_id == telegram_id, Admin.is_active == True)
        .first()
    )
    return admin is not None


def get_admin(session: Session, telegram_id: int) -> Admin | None:
    return (
        session.query(Admin)
        .filter(Admin.telegram_id == telegram_id, Admin.is_active == True)
        .first()
    )


def is_super_admin(session: Session, telegram_id: int) -> bool:
    admin = get_admin(session, telegram_id)
    return admin is not None and admin.role == "super"
