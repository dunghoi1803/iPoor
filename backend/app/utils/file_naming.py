from unicodedata import normalize

FILENAME_SEPARATOR = "_"
FILENAME_MAX_LENGTH = 160
POLICY_CATEGORY_VI = {
    "decree": "chính-sách",
    "report": "báo-cáo",
    "guideline": "hướng-dẫn",
    "guidline": "hướng-dẫn",
    "circular": "thông-tư",
    "news": "tin-tức",
    "announcement": "thông-báo",
}
POVERTY_STATUS_VI = {
    "poor": "nghèo",
    "near_poor": "cận-nghèo",
    "escaped_poverty": "thoát-nghèo",
    "at_risk": "nguy-cơ-tái-nghèo",
}


def slugify_filename(value: str) -> str:
    normalized = normalize("NFC", value or "").strip().lower()
    if not normalized:
        return "unknown"
    result: list[str] = []
    last_sep = False
    for ch in normalized:
        if ch.isalnum():
            result.append(ch)
            last_sep = False
        elif ch in {" ", "-", "_"}:
            if not last_sep:
                result.append("-")
                last_sep = True
        else:
            continue
    return "".join(result).strip("-") or "unknown"


def translate_policy_category(category: str | None) -> str:
    if not category:
        return ""
    return POLICY_CATEGORY_VI.get(category.strip().lower(), category)


def translate_poverty_status(status: str | None) -> str:
    if not status:
        return ""
    return POVERTY_STATUS_VI.get(status.strip().lower(), status)


def build_household_prefix(
    household_code: str | None,
    poverty_status: str | None,
    head_name: str | None,
    id_card: str | None,
) -> str:
    status_label = translate_poverty_status(poverty_status)
    parts = [
        slugify_filename(household_code or ""),
        slugify_filename(status_label),
        slugify_filename(head_name or ""),
        slugify_filename(id_card or ""),
    ]
    return FILENAME_SEPARATOR.join(parts)


