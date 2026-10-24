"""بازیابی ترکیبی متنی و معنایی (TF-IDF محلی، بدون API پولی)"""
from __future__ import annotations
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session, joinedload
from database.models import Question, QuestionKeyword, Category, Service
from utils.persian_text import normalize_for_search, normalize_persian

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeChunk:
    question_id: int
    question_text: str
    answer_text: str
    category_path: str
    service_title: str
    keywords: List[str]
    source_file: str
    source_row: Optional[int]
    updated_at: Optional[str]
    # متن ترکیبی برای ایندکس
    index_text: str = ""


@dataclass
class RetrievalResult:
    chunk: KnowledgeChunk
    score: float
    match_type: str  # keyword | tfidf | hybrid


class HybridRetriever:
    """
    بازیابی ترکیبی:
    1) امتیاز کلیدواژه‌ای (مشابه search_service)
    2) امتیاز TF-IDF محلی روی فارسی نرمال‌شده
    3) ترکیب وزنی
    """

    def __init__(self):
        self._chunks: List[KnowledgeChunk] = []
        self._idf: Dict[str, float] = {}
        self._doc_tf: List[Dict[str, float]] = []
        self._built = False

    def rebuild(self, session: Session) -> int:
        """بازسازی ایندکس از پرسش‌های فعال دیتابیس"""
        questions = (
            session.query(Question)
            .options(
                joinedload(Question.keywords),
                joinedload(Question.category),
                joinedload(Question.service),
            )
            .filter(Question.is_active == True)
            .all()
        )
        chunks: List[KnowledgeChunk] = []
        for q in questions:
            path_parts = []
            cat = q.category
            while cat:
                path_parts.insert(0, cat.name or "")
                cat = cat.parent if cat.parent_id else None
            kw = [k.keyword for k in (q.keywords or []) if k.keyword]
            svc = (q.service.title if q.service else "") or ""
            index_parts = [
                q.question_text or "",
                q.answer_text or "",
                " ".join(kw),
                svc,
                " ".join(path_parts),
            ]
            chunk = KnowledgeChunk(
                question_id=q.id,
                question_text=q.question_text or "",
                answer_text=q.answer_text or "",
                category_path=" › ".join(path_parts),
                service_title=svc,
                keywords=kw,
                source_file=q.source_file or "",
                source_row=q.source_row,
                updated_at=str(q.updated_at) if q.updated_at else None,
                index_text=normalize_for_search(" ".join(index_parts)),
            )
            chunks.append(chunk)

        self._chunks = chunks
        self._build_tfidf()
        self._built = True
        logger.info("Retriever index rebuilt: %d chunks", len(chunks))
        return len(chunks)

    _STOP = frozenset({
        "است", "هست", "چیست", "چقدر", "چگونه", "آیا", "می", "شود", "باشد",
        "برای", "این", "آن", "که", "را", "از", "به", "در", "با", "یا", "و",
        "یک", "هم", "اگر", "چه", "کی", "کجا", "چرا", "من", "ما", "شما",
        "دارم", "دارد", "دارند", "کنم", "کند", "لطفا", "سلام", "امروز",
        "قیمت", "بازار",
    })

    def _tokenize(self, text: str) -> List[str]:
        text = normalize_for_search(text)
        return [t for t in text.split() if len(t) >= 2 and t not in self._STOP]

    def _build_tfidf(self):
        n = len(self._chunks)
        if n == 0:
            self._idf = {}
            self._doc_tf = []
            return
        df: Counter = Counter()
        doc_tf: List[Dict[str, float]] = []
        for ch in self._chunks:
            tokens = self._tokenize(ch.index_text)
            tf = Counter(tokens)
            total = sum(tf.values()) or 1
            doc_tf.append({t: c / total for t, c in tf.items()})
            for t in set(tokens):
                df[t] += 1
        self._idf = {t: math.log((n + 1) / (df_t + 1)) + 1.0 for t, df_t in df.items()}
        self._doc_tf = doc_tf

    def _keyword_score(self, query_tokens: List[str], chunk: KnowledgeChunk) -> float:
        if not query_tokens:
            return 0.0
        q_text = normalize_for_search(chunk.question_text)
        a_text = normalize_for_search(chunk.answer_text)
        kw_text = normalize_for_search(" ".join(chunk.keywords))
        full_q = " ".join(query_tokens)
        score = 0.0
        if full_q in q_text:
            score += 50
        if full_q in a_text:
            score += 15
        if full_q in kw_text:
            score += 25
        for t in query_tokens:
            if t in q_text:
                score += 10
            if t in a_text:
                score += 3
            if t in kw_text:
                score += 8
            if t in normalize_for_search(chunk.service_title):
                score += 5
            if t in normalize_for_search(chunk.category_path):
                score += 4
        return score

    def _tfidf_score(self, query_tokens: List[str], doc_idx: int) -> float:
        if not query_tokens or doc_idx >= len(self._doc_tf):
            return 0.0
        q_tf = Counter(query_tokens)
        q_total = sum(q_tf.values()) or 1
        q_vec = {t: (c / q_total) * self._idf.get(t, 1.0) for t, c in q_tf.items()}
        d_vec = {
            t: tf * self._idf.get(t, 1.0)
            for t, tf in self._doc_tf[doc_idx].items()
        }
        # cosine
        dot = sum(q_vec.get(t, 0) * d_vec.get(t, 0) for t in q_vec)
        nq = math.sqrt(sum(v * v for v in q_vec.values())) or 1e-9
        nd = math.sqrt(sum(v * v for v in d_vec.values())) or 1e-9
        return dot / (nq * nd)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_hybrid_score: float = 8.0,
    ) -> List[RetrievalResult]:
        if not self._built or not self._chunks:
            return []

        tokens = self._tokenize(query)
        if not tokens:
            return []

        results: List[RetrievalResult] = []
        for i, chunk in enumerate(self._chunks):
            kw_s = self._keyword_score(tokens, chunk)
            tf_s = self._tfidf_score(tokens, i)
            # نرمال‌سازی تقریبی: TF-IDF در [0,1]، keyword اغلب 0–80
            hybrid = kw_s + (tf_s * 40.0)
            if hybrid >= min_hybrid_score * 0.5:  # کاندیداهای اولیه
                results.append(
                    RetrievalResult(
                        chunk=chunk,
                        score=hybrid,
                        match_type="hybrid",
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)


# نمونه سراسری (در حافظه؛ پس از تغییر محتوا rebuild می‌شود)
_global_retriever: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = HybridRetriever()
    return _global_retriever


def ensure_index(session: Session) -> int:
    ret = get_retriever()
    if not ret._built:
        return ret.rebuild(session)
    return ret.chunk_count
