"""سرویس مدیریت دسته‌بندی‌ها"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from database.models import Category


def get_root_categories(session: Session, active_only: bool = True) -> List[Category]:
    q = session.query(Category).filter(Category.parent_id.is_(None))
    if active_only:
        q = q.filter(Category.is_active == True)
    return q.order_by(Category.sort_order, Category.name).all()


def get_children(session: Session, parent_id: int, active_only: bool = True) -> List[Category]:
    q = session.query(Category).filter(Category.parent_id == parent_id)
    if active_only:
        q = q.filter(Category.is_active == True)
    return q.order_by(Category.sort_order, Category.name).all()


def get_category(session: Session, cat_id: int) -> Optional[Category]:
    return session.query(Category).filter(Category.id == cat_id).first()


def get_or_create_category(
    session: Session,
    name: str,
    parent_id: Optional[int] = None,
    source_file: str = None,
    sort_order: int = 0,
) -> Category:
    q = session.query(Category).filter(
        Category.name == name,
        Category.parent_id == parent_id if parent_id else Category.parent_id.is_(None),
    )
    existing = q.first()
    if existing:
        return existing
    cat = Category(
        name=name.strip(),
        parent_id=parent_id,
        source_file=source_file,
        sort_order=sort_order,
    )
    session.add(cat)
    session.flush()
    return cat


def create_category(
    session: Session,
    name: str,
    parent_id: Optional[int] = None,
    description: str = "",
    sort_order: int = 0,
) -> Category:
    cat = Category(
        name=name.strip(),
        parent_id=parent_id,
        description=description,
        sort_order=sort_order,
    )
    session.add(cat)
    session.flush()
    return cat


def update_category(session: Session, cat_id: int, **kwargs) -> Optional[Category]:
    cat = get_category(session, cat_id)
    if not cat:
        return None
    for k, v in kwargs.items():
        if hasattr(cat, k) and k not in ("id", "created_at"):
            setattr(cat, k, v)
    session.flush()
    return cat


def delete_category(session: Session, cat_id: int, cascade: bool = False) -> bool:
    cat = get_category(session, cat_id)
    if not cat:
        return False
    if not cascade and (cat.children or cat.questions or cat.services):
        return False
    session.delete(cat)
    session.flush()
    return True


def get_path(session: Session, cat_id: int) -> List[str]:
    """مسیر کامل دسته‌بندی از ریشه"""
    path = []
    cat = get_category(session, cat_id)
    while cat:
        path.insert(0, cat.name)
        cat = cat.parent if cat.parent_id else None
    return path


def count_categories(session: Session, active_only: bool = False) -> int:
    q = session.query(Category)
    if active_only:
        q = q.filter(Category.is_active == True)
    return q.count()
