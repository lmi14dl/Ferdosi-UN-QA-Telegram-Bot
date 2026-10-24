"""مدل‌های پایگاه داده"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
    UniqueConstraint, Index, Float
)
from sqlalchemy.orm import relationship
from database.connection import Base


def utcnow():
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    source_file = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    parent = relationship("Category", remote_side=[id], backref="children")
    services = relationship("Service", back_populates="category", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_categories_parent", "parent_id"),
        Index("ix_categories_active", "is_active"),
    )

    def __repr__(self):
        return f"<Category {self.id}: {self.name}>"


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    source_file = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    category = relationship("Category", back_populates="services")
    questions = relationship("Question", back_populates="service", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Service {self.id}: {self.title}>"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    source_file = Column(String(100), nullable=True)
    source_row = Column(Integer, nullable=True)
    source_hash = Column(String(64), nullable=True, unique=True)  # برای جلوگیری از تکرار
    admin_notes = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    category = relationship("Category", back_populates="questions")
    service = relationship("Service", back_populates="questions")
    keywords = relationship("QuestionKeyword", back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_questions_active", "is_active"),
        Index("ix_questions_category", "category_id"),
        Index("ix_questions_service", "service_id"),
    )

    def __repr__(self):
        return f"<Question {self.id}: {self.question_text[:40]}>"


class QuestionKeyword(Base):
    __tablename__ = "question_keywords"

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    keyword = Column(String(100), nullable=False)

    question = relationship("Question", back_populates="keywords")

    __table_args__ = (
        UniqueConstraint("question_id", "keyword", name="uq_q_keyword"),
        Index("ix_keywords_keyword", "keyword"),
    )


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String(150), default="")
    role = Column(String(50), default="content")  # super | content
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    created_by = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Admin {self.telegram_id} ({self.role})>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    full_name = Column(String(200), nullable=True)
    first_seen = Column(DateTime, default=utcnow)
    last_seen = Column(DateTime, default=utcnow)
    activity_count = Column(Integer, default=0)


class UserActivity(Base):
    __tablename__ = "user_activity"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    telegram_id = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)  # view_question, search, start, ...
    target_id = Column(Integer, nullable=True)
    detail = Column(String(255), default="")
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_activity_created", "created_at"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    admin_telegram_id = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True)
    source_file = Column(String(255), nullable=False)
    status = Column(String(30), default="running")  # running, success, partial, failed
    total_rows = Column(Integer, default=0)
    imported = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    report = Column(Text, default="")
    started_at = Column(DateTime, default=utcnow)
    finished_at = Column(DateTime, nullable=True)


class ContactPoint(Base):
    __tablename__ = "contact_points"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    unit = Column(String(150), default="")
    phone = Column(String(50), default="")
    internal = Column(String(20), default="")
    address = Column(Text, default="")
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
