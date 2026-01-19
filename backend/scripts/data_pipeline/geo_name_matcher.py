import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Optional
from unicodedata import normalize

EMPTY_STRING = ""
SPACE_REGEX = re.compile(r"\s+")
NON_WORD_REGEX = re.compile(r"[^a-z0-9 ]+")
LEADING_ZERO_REGEX = re.compile(r"^0+")
PAREN_REGEX = re.compile(r"\(.*?\)")
FUZZY_MATCH_THRESHOLD = 0.92
MIN_FUZZY_LENGTH = 4
ABBREVIATIONS = {
    "tp": "thanh pho",
}
STOPWORDS = {
    "tinh",
    "thanh",
    "pho",
}
ALIAS_KEY_MAP = {
    "hue": "thua thien hue",
    "tp ho chi minh": "thanh pho ho chi minh",
    "br vt": "ba ria vung tau",
    "dac lak": "dak lak",
}


def normalize_text(value: Any) -> str:
    if value is None:
        return EMPTY_STRING
    text = normalize("NFC", str(value))
    return " ".join(text.split()).strip()


def strip_diacritics(value: str) -> str:
    decomposed = normalize("NFD", value)
    stripped = "".join(
        ch for ch in decomposed if unicodedata.category(ch) != "Mn"
    )
    return stripped.replace("đ", "d").replace("Đ", "D")


def normalize_name_key(value: str) -> str:
    text = normalize_text(value).lower()
    text = strip_diacritics(text)
    text = PAREN_REGEX.sub(" ", text)
    text = NON_WORD_REGEX.sub(" ", text)
    text = SPACE_REGEX.sub(" ", text).strip()
    expanded = " ".join(ABBREVIATIONS.get(token, token) for token in text.split(" "))
    tokens = expanded.split(" ")
    tokens = [token for token in tokens if token and token not in STOPWORDS]
    key = " ".join(tokens).strip()
    return ALIAS_KEY_MAP.get(key, key)


def normalize_geo_code(raw_code: Any) -> str:
    if raw_code is None:
        return EMPTY_STRING
    raw = str(raw_code).strip()
    if not raw:
        return EMPTY_STRING
    trimmed = LEADING_ZERO_REGEX.sub(EMPTY_STRING, raw)
    return trimmed or raw


def build_label_lookup(label_map: dict[str, str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for _, name in label_map.items():
        if not name:
            continue
        key = normalize_name_key(name)
        if key and key not in lookup:
            lookup[key] = name
    return lookup


def find_best_match(key: str, lookup: dict[str, str]) -> Optional[str]:
    if not key or len(key) < MIN_FUZZY_LENGTH:
        return None
    best_score = 0.0
    best_name = None
    for candidate, name in lookup.items():
        score = SequenceMatcher(None, key, candidate).ratio()
        if score > best_score:
            best_score = score
            best_name = name
    if best_score >= FUZZY_MATCH_THRESHOLD:
        return best_name
    return None


def resolve_geo_name(label: str, lookup: dict[str, str]) -> str:
    if not label:
        return label
    key = normalize_name_key(label)
    if key in lookup:
        return lookup[key]
    best = find_best_match(key, lookup)
    return best or label
