"""ابزار صفحه‌بندی"""
from typing import List, TypeVar, Tuple

T = TypeVar("T")


def paginate(items: List[T], page: int, per_page: int = 8) -> Tuple[List[T], int, int]:
    """
    برمی‌گرداند: (آیتم‌های صفحه فعلی، شماره صفحه، تعداد کل صفحات)
    """
    total = len(items)
    if total == 0:
        return [], 1, 1
    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], page, total_pages
