import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from ..utils.text import normalize_search_text

router = APIRouter(prefix="/locations", tags=["locations"])

DATA_FILE = "communes.json"
COMMUNES_CACHE: dict[str, list[str]] | None = None
COMMUNES_INDEX: dict[str, str] | None = None
PROVINCES_CACHE: list[str] | None = None


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_communes() -> tuple[dict[str, list[str]], dict[str, str]]:
    global COMMUNES_CACHE, COMMUNES_INDEX, PROVINCES_CACHE
    if COMMUNES_CACHE is not None and COMMUNES_INDEX is not None:
        return COMMUNES_CACHE, COMMUNES_INDEX

    path = get_repo_root() / "backend" / "app" / "data" / DATA_FILE
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commune dataset not found")

    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    communes: dict[str, list[str]] = {}
    index: dict[str, str] = {}
    for province_name, items in data.items():
        if not isinstance(items, list):
            continue
        communes[province_name] = [str(item).strip() for item in items if str(item).strip()]
        index[normalize_search_text(province_name)] = province_name

    COMMUNES_CACHE = communes
    COMMUNES_INDEX = index
    PROVINCES_CACHE = list(communes.keys())
    return communes, index


def resolve_province_key(province: str, index: dict[str, str]) -> str | None:
    normalized = normalize_search_text(province)
    if normalized in index:
        return index[normalized]
    for key, value in index.items():
        if normalized in key or key in normalized:
            return value
    return None


@router.get("/communes")
def list_communes(
    province: str = Query(..., min_length=1),
    q: str | None = Query(None),
    limit: int = Query(20, ge=1, le=20),
) -> dict[str, Any]:
    communes, index = load_communes()
    province_key = resolve_province_key(province, index)
    if not province_key:
        return {"items": [], "total": 0, "limit": limit}

    items = communes.get(province_key, [])
    if q:
        query = normalize_search_text(q)
        items = [item for item in items if query in normalize_search_text(item)]

    limited = items[:limit]
    return {
        "items": [{"name": item} for item in limited],
        "total": len(items),
        "limit": limit,
    }


@router.get("/provinces")
def list_provinces(
    q: str | None = Query(None),
    limit: int = Query(20, ge=1, le=20),
) -> dict[str, Any]:
    load_communes()
    provinces = PROVINCES_CACHE or []
    if q:
        query = normalize_search_text(q)
        provinces = [item for item in provinces if query in normalize_search_text(item)]
    limited = provinces[:limit]
    return {
        "items": [{"name": item} for item in limited],
        "total": len(provinces),
        "limit": limit,
    }
