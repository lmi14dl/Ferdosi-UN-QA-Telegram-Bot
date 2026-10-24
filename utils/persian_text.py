"""نرمال‌سازی و ابزارهای متن فارسی"""
import re
from typing import List

_ARABIC_PUNCT = "؟،؛«»ـ"
_LATIN_PUNCT = "?!,.:;\"'()[]{}\\-_/\\\\"


def normalize_persian(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = text.replace("\u200c", " ").replace("\u200f", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_for_search(text: str) -> str:
    text = normalize_persian(text)
    text = text.lower()
    # حذف همه علائم غیر حرف/عدد/فاصله
    out = []
    for ch in text:
        o = ord(ch)
        if ch.isspace():
            out.append(" ")
        elif ch.isalnum() or 0x0600 <= o <= 0x06FF:
            # حذف علائم عربی داخل بازه
            if ch in _ARABIC_PUNCT or ch in "؟!٬٫":
                out.append(" ")
            else:
                out.append(ch)
        else:
            out.append(" ")
    text = "".join(out)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text: str, max_len: int = 60) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def split_long_message(text: str, max_len: int = 4000) -> List[str]:
    if not text or len(text) <= max_len:
        return [text or ""]
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = max_len
        parts.append(text[:split_at].rstrip())
        text = text[split_at:].lstrip()
    return parts
