from typing import Any
from unicodedata import normalize


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = normalize("NFC", str(value))
    return " ".join(text.split()).strip()


def normalize_header(value: Any) -> str:
    if value is None:
        return ""
    text = normalize("NFC", str(value))
    return " ".join(text.split()).strip().lower()


def normalize_search_text(value: Any) -> str:
    return normalize_text(value).casefold()
