import csv
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/gis", tags=["gis"])

GEOJSON_FILES = {
    "old_63": "Việt Nam (tỉnh thành) - 63.geojson",
    "new_34": "Việt Nam (tỉnh thành) - 34.geojson",
}
DATA_FILE = "gis_indicator_values.csv"
DEFAULT_GEO_VERSION = "old_63"
CACHE_MAX_ENTRIES = 50
CACHE: dict[str, dict[str, Any]] = {}
CACHE_ORDER: list[str] = []


def get_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "FE" / "data").exists():
            return parent
    return here.parents[2]


def load_geojson(geo_version: str) -> dict[str, Any]:
    filename = GEOJSON_FILES.get(geo_version)
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid geo_version")
    path = get_repo_root() / "FE" / "data" / filename
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GeoJSON not found")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_indicator_rows(
    indicator_code: str,
    year: int,
    geo_version: str,
    metric: str | None,
) -> dict[str, dict[str, Any]]:
    path = get_repo_root() / "FE" / "data" / "processed" / DATA_FILE
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS dataset not found")

    records: dict[str, dict[str, Any]] = {}
    multi_metric = False
    with path.open(encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("indicator_code") != indicator_code:
                continue
            if row.get("geo_version") != geo_version:
                continue
            if str(row.get("year")) != str(year):
                continue
            row_metric = row.get("metric") or ""
            if metric and row_metric != metric:
                continue
            geo_code = row.get("geo_code") or ""
            if not geo_code:
                continue
            if geo_code in records and row_metric:
                multi_metric = True
            records[geo_code] = row

    if not metric and multi_metric:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metric is required for this indicator",
        )
    return records


def cache_get(key: str) -> dict[str, Any] | None:
    return CACHE.get(key)


def cache_set(key: str, value: dict[str, Any]) -> None:
    if key in CACHE:
        return
    CACHE[key] = value
    CACHE_ORDER.append(key)
    if len(CACHE_ORDER) > CACHE_MAX_ENTRIES:
        oldest = CACHE_ORDER.pop(0)
        CACHE.pop(oldest, None)


@router.get("/indicators")
def list_indicators() -> list[dict[str, Any]]:
    path = get_repo_root() / "FE" / "data" / "processed" / DATA_FILE
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS dataset not found")

    indicators: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            code = row.get("indicator_code") or ""
            if not code:
                continue
            entry = indicators.setdefault(
                code,
                {
                    "indicator_code": code,
                    "indicator_title": row.get("indicator_title") or "",
                    "metrics": set(),
                    "years": set(),
                    "geo_versions": set(),
                },
            )
            metric = row.get("metric") or ""
            year = row.get("year") or ""
            geo_version = row.get("geo_version") or ""
            if metric:
                entry["metrics"].add(metric)
            if year:
                entry["years"].add(year)
            if geo_version:
                entry["geo_versions"].add(geo_version)

    result: list[dict[str, Any]] = []
    for item in indicators.values():
        result.append(
            {
                "indicator_code": item["indicator_code"],
                "indicator_title": item["indicator_title"],
                "metrics": sorted(item["metrics"]),
                "years": sorted(item["years"]),
                "geo_versions": sorted(item["geo_versions"]),
            }
        )
    return sorted(result, key=lambda x: x["indicator_code"])


@router.get("/indicators/{indicator_code}/metrics")
def list_indicator_metrics(indicator_code: str) -> dict[str, Any]:
    path = get_repo_root() / "FE" / "data" / "processed" / DATA_FILE
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS dataset not found")

    metrics: set[str] = set()
    years: set[str] = set()
    geo_versions: set[str] = set()
    indicator_title = ""

    with path.open(encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("indicator_code") != indicator_code:
                continue
            if not indicator_title:
                indicator_title = row.get("indicator_title") or ""
            metric = row.get("metric") or ""
            year = row.get("year") or ""
            geo_version = row.get("geo_version") or ""
            if metric:
                metrics.add(metric)
            if year:
                years.add(year)
            if geo_version:
                geo_versions.add(geo_version)

    if not metrics and not years and not geo_versions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found")

    metrics_sorted = sorted(metrics)
    return {
        "indicator_code": indicator_code,
        "indicator_title": indicator_title,
        "metrics": metrics_sorted,
        "default_metric": metrics_sorted[0] if metrics_sorted else None,
        "years": sorted(years),
        "geo_versions": sorted(geo_versions),
    }


@router.get("/geojson")
def get_geojson(
    indicator: str = Query(..., min_length=1),
    year: int = Query(..., ge=1900, le=2100),
    geo_version: str = Query(DEFAULT_GEO_VERSION),
    metric: str | None = Query(None),
) -> dict[str, Any]:
    cache_key = f"{indicator}:{year}:{geo_version}:{metric or ''}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    geojson = load_geojson(geo_version)
    rows = load_indicator_rows(indicator, year, geo_version, metric)
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        geo_code = str(props.get("ma_tinh") or "")
        record = rows.get(geo_code)
        if record:
            props["value"] = float(record.get("value"))
            props["indicator"] = record.get("indicator_code")
            props["metric"] = record.get("metric")
            props["year"] = int(record.get("year"))
        else:
            props["value"] = None
            props["indicator"] = indicator
            props["metric"] = metric
            props["year"] = year
        feature["properties"] = props
    cache_set(cache_key, geojson)
    return geojson


@router.get("/values")
def get_values(
    indicator: str = Query(..., min_length=1),
    year: int = Query(..., ge=1900, le=2100),
    geo_version: str = Query(DEFAULT_GEO_VERSION),
    metric: str | None = Query(None),
) -> dict[str, Any]:
    cache_key = f"values:{indicator}:{year}:{geo_version}:{metric or ''}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    rows = load_indicator_rows(indicator, year, geo_version, metric)
    values: dict[str, float] = {}
    for geo_code, row in rows.items():
        raw_value = row.get("value")
        if raw_value is None:
            continue
        try:
            values[geo_code] = float(raw_value)
        except (TypeError, ValueError):
            continue

    payload = {
        "indicator": indicator,
        "metric": metric,
        "year": year,
        "geo_version": geo_version,
        "values": values,
    }
    cache_set(cache_key, payload)
    return payload
