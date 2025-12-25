import csv
import json
import re
from pathlib import Path
from unicodedata import normalize

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import deps, models, schemas

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DATA_FILE_NAME = "gis_indicator_values.csv"
REGION_FILE_NAME = "region_map.json"
DEFAULT_GEO_VERSION = "old_63"
DEFAULT_METRIC = "count_households"
POOR_INDICATOR_CODE = "1.3"
NEAR_POOR_INDICATOR_CODE = "1.5"
CSV_ENCODING = "utf-8-sig"

FIELD_INDICATOR = "indicator_code"
FIELD_YEAR = "year"
FIELD_METRIC = "metric"
FIELD_GEO_VERSION = "geo_version"
FIELD_GEO_NAME = "geo_name"
FIELD_VALUE = "value"

REGION_MAP_KEY = "province_to_region"
SCOPE_COUNTRY = "country"
SCOPE_REGION = "region"
SCOPE_PROVINCE = "province"
REGION_METRIC_POOR = "poor"
REGION_METRIC_NEAR_POOR = "near_poor"


def get_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "FE" / "data").exists():
            return parent
    return here.parents[2]


def normalize_location(value: str) -> str:
    text = normalize("NFC", value).lower()
    text = text.replace(".", "")
    text = re.sub(r"thanh\s*pho\s*", "tp ", text)
    text = re.sub(r"tp\s*", "tp ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_csv_rows() -> list[dict[str, str]]:
    path = get_repo_root() / "FE" / "data" / "processed" / DATA_FILE_NAME
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard dataset not found")
    with path.open(encoding=CSV_ENCODING) as handle:
        return list(csv.DictReader(handle))


def load_region_map() -> dict[str, str]:
    path = get_repo_root() / "FE" / "data" / "processed" / REGION_FILE_NAME
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region map not found")
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    region_map: dict[str, str] = {}
    for province, region in (payload.get(REGION_MAP_KEY) or {}).items():
        region_map[normalize_location(province)] = (region or "").strip()
    return region_map


def load_region_reverse(region_map: dict[str, str]) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for province, region in region_map.items():
        normalized_region = normalize_location(region)
        output.setdefault(normalized_region, []).append(province)
    return output


def unique_provinces(rows: list[dict[str, str]]) -> list[str]:
    provinces = {
        (row.get(FIELD_GEO_NAME) or "").strip()
        for row in rows
        if row.get(FIELD_GEO_NAME)
    }
    return sorted({name for name in provinces if name})


def sum_by_year(rows: list[dict[str, str]]) -> dict[int, float]:
    totals: dict[int, float] = {}
    for row in rows:
        try:
            year = int(row.get(FIELD_YEAR) or 0)
            value = float(row.get(FIELD_VALUE) or 0)
        except (TypeError, ValueError):
            continue
        totals[year] = totals.get(year, 0.0) + value
    return totals


def percent_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


def filter_rows(
    rows: list[dict[str, str]],
    indicator_code: str,
    metric: str,
    geo_version: str,
) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row.get(FIELD_INDICATOR) == indicator_code
        and row.get(FIELD_METRIC) == metric
        and row.get(FIELD_GEO_VERSION) == geo_version
    ]


def resolve_scope_name(scope: str, name: str | None) -> str | None:
    if scope == SCOPE_COUNTRY:
        return None
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required")
    return normalize_location(name)


def apply_scope_filter(
    rows: list[dict[str, str]],
    scope: str,
    scope_name: str | None,
) -> list[dict[str, str]]:
    if scope == SCOPE_COUNTRY or not scope_name:
        return rows
    if scope == SCOPE_REGION:
        region_map = load_region_map()
        reverse_map = load_region_reverse(region_map)
        provinces = reverse_map.get(scope_name)
        if not provinces:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region not found")
        province_set = set(provinces)
        return [
            row
            for row in rows
            if normalize_location(row.get(FIELD_GEO_NAME) or "") in province_set
        ]
    if scope == SCOPE_PROVINCE:
        return [
            row
            for row in rows
            if normalize_location(row.get(FIELD_GEO_NAME) or "") == scope_name
        ]
    return rows


def build_region_totals(
    rows: list[dict[str, str]],
    region_map: dict[str, str],
    target_year: int,
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in rows:
        try:
            row_year = int(row.get(FIELD_YEAR) or 0)
        except (TypeError, ValueError):
            continue
        if row_year != target_year:
            continue
        province = normalize_location(row.get(FIELD_GEO_NAME) or "")
        region = region_map.get(province)
        if not region:
            continue
        try:
            value = float(row.get(FIELD_VALUE) or 0)
        except (TypeError, ValueError):
            continue
        totals[region] = totals.get(region, 0.0) + value
    return totals


@router.get("/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardSummary:
    rows = load_csv_rows()
    poor_rows = filter_rows(rows, POOR_INDICATOR_CODE, DEFAULT_METRIC, DEFAULT_GEO_VERSION)
    near_poor_rows = filter_rows(rows, NEAR_POOR_INDICATOR_CODE, DEFAULT_METRIC, DEFAULT_GEO_VERSION)
    if not poor_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard data missing")

    poor_by_year = sum_by_year(poor_rows)
    near_poor_by_year = sum_by_year(near_poor_rows)
    years = sorted(set(poor_by_year.keys()) | set(near_poor_by_year.keys()))
    if not years:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard data missing")

    latest_year = max(years)
    previous_years = [year for year in years if year < latest_year]
    previous_year = max(previous_years) if previous_years else None

    latest_poor = poor_by_year.get(latest_year, 0.0)
    latest_near_poor = near_poor_by_year.get(latest_year, 0.0)
    previous_poor = poor_by_year.get(previous_year, 0.0) if previous_year else 0.0
    previous_near_poor = near_poor_by_year.get(previous_year, 0.0) if previous_year else 0.0

    poor_delta = percent_change(latest_poor, previous_poor)
    near_poor_delta = percent_change(latest_near_poor, previous_near_poor)
    exit_poverty_total = (
        abs((latest_poor + latest_near_poor) - (previous_poor + previous_near_poor))
        if previous_year
        else 0.0
    )

    series_poor = [poor_by_year.get(year, 0.0) for year in years]
    series_near_poor = [near_poor_by_year.get(year, 0.0) for year in years]
    series_exit = []
    for index, year in enumerate(years):
        if index == 0:
            series_exit.append(0.0)
            continue
        previous_value = series_poor[index - 1]
        current_value = series_poor[index]
        series_exit.append(max(previous_value - current_value, 0.0))

    region_map = load_region_map()
    region_totals = build_region_totals(poor_rows, region_map, latest_year)

    top_regions = sorted(
        ({"label": region, "value": value} for region, value in region_totals.items()),
        key=lambda item: item["value"],
        reverse=True,
    )

    return schemas.DashboardSummary(
        latest_year=latest_year,
        poor_total=latest_poor,
        poor_delta_percent=poor_delta,
        near_poor_total=latest_near_poor,
        near_poor_delta_percent=near_poor_delta,
        exit_poverty_total=exit_poverty_total,
        at_risk_total=None,
        at_risk_note=None,
        series=schemas.DashboardSeries(
            years=years,
            poor=series_poor,
            near_poor=series_near_poor,
            exit_poverty=series_exit,
        ),
        top_regions=[schemas.DashboardRegionItem(**item) for item in top_regions],
    )


@router.get("/regions", response_model=list[schemas.DashboardRegionItem])
def get_region_comparison(
    metric: str = Query(REGION_METRIC_POOR, pattern="^(poor|near_poor)$"),
    current_user: models.User = Depends(deps.get_current_user),
) -> list[schemas.DashboardRegionItem]:
    rows = load_csv_rows()
    indicator_code = POOR_INDICATOR_CODE if metric == REGION_METRIC_POOR else NEAR_POOR_INDICATOR_CODE
    selected_rows = filter_rows(rows, indicator_code, DEFAULT_METRIC, DEFAULT_GEO_VERSION)
    if not selected_rows:
        return []
    totals_by_year = sum_by_year(selected_rows)
    years = sorted(totals_by_year.keys())
    if not years:
        return []
    latest_year = max(years)
    region_map = load_region_map()
    region_totals = build_region_totals(selected_rows, region_map, latest_year)
    items = sorted(
        (schemas.DashboardRegionItem(label=region, value=value) for region, value in region_totals.items()),
        key=lambda item: item.value,
        reverse=True,
    )
    return items


@router.get("/filters", response_model=schemas.DashboardTrendOptions)
def get_dashboard_filters(
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardTrendOptions:
    rows = load_csv_rows()
    base_rows = filter_rows(rows, POOR_INDICATOR_CODE, DEFAULT_METRIC, DEFAULT_GEO_VERSION)
    region_map = load_region_map()
    regions = sorted({region for region in region_map.values() if region})
    provinces = sorted({name for name in unique_provinces(base_rows)})
    return schemas.DashboardTrendOptions(regions=regions, provinces=provinces)


@router.get("/trend", response_model=schemas.DashboardSeries)
def get_dashboard_trend(
    scope: str = Query(SCOPE_COUNTRY, pattern="^(country|region|province)$"),
    name: str | None = Query(None),
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardSeries:
    rows = load_csv_rows()
    poor_rows = filter_rows(rows, POOR_INDICATOR_CODE, DEFAULT_METRIC, DEFAULT_GEO_VERSION)
    near_poor_rows = filter_rows(rows, NEAR_POOR_INDICATOR_CODE, DEFAULT_METRIC, DEFAULT_GEO_VERSION)
    if not poor_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard data missing")

    scope_name = resolve_scope_name(scope, name)
    poor_rows = apply_scope_filter(poor_rows, scope, scope_name)
    near_poor_rows = apply_scope_filter(near_poor_rows, scope, scope_name)

    poor_by_year = sum_by_year(poor_rows)
    near_poor_by_year = sum_by_year(near_poor_rows)
    years = sorted(set(poor_by_year.keys()) | set(near_poor_by_year.keys()))
    series_poor = [poor_by_year.get(year, 0.0) for year in years]
    series_near_poor = [near_poor_by_year.get(year, 0.0) for year in years]

    series_exit = []
    for index, year in enumerate(years):
        if index == 0:
            series_exit.append(0.0)
            continue
        previous_value = series_poor[index - 1]
        current_value = series_poor[index]
        series_exit.append(max(previous_value - current_value, 0.0))

    return schemas.DashboardSeries(
        years=years,
        poor=series_poor,
        near_poor=series_near_poor,
        exit_poverty=series_exit,
    )


@router.get("/kpis", response_model=schemas.DashboardKpis)
def get_dashboard_kpis(
    scope: str = Query(SCOPE_COUNTRY, pattern="^(country|region|province)$"),
    name: str | None = Query(None),
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardKpis:
    rows = load_csv_rows()
    poor_rows = filter_rows(rows, POOR_INDICATOR_CODE, DEFAULT_METRIC, DEFAULT_GEO_VERSION)
    near_poor_rows = filter_rows(rows, NEAR_POOR_INDICATOR_CODE, DEFAULT_METRIC, DEFAULT_GEO_VERSION)
    if not poor_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard data missing")

    scope_name = resolve_scope_name(scope, name)
    poor_rows = apply_scope_filter(poor_rows, scope, scope_name)
    near_poor_rows = apply_scope_filter(near_poor_rows, scope, scope_name)

    poor_by_year = sum_by_year(poor_rows)
    near_poor_by_year = sum_by_year(near_poor_rows)
    years = sorted(set(poor_by_year.keys()) | set(near_poor_by_year.keys()))
    if not years:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard data missing")

    latest_year = max(years)
    previous_years = [year for year in years if year < latest_year]
    previous_year = max(previous_years) if previous_years else None

    latest_poor = poor_by_year.get(latest_year, 0.0)
    latest_near_poor = near_poor_by_year.get(latest_year, 0.0)
    previous_poor = poor_by_year.get(previous_year, 0.0) if previous_year else 0.0
    previous_near_poor = near_poor_by_year.get(previous_year, 0.0) if previous_year else 0.0

    poor_delta = percent_change(latest_poor, previous_poor)
    near_poor_delta = percent_change(latest_near_poor, previous_near_poor)
    exit_poverty_total = (
        abs((latest_poor + latest_near_poor) - (previous_poor + previous_near_poor))
        if previous_year
        else 0.0
    )

    return schemas.DashboardKpis(
        latest_year=latest_year,
        poor_total=latest_poor,
        poor_delta_percent=poor_delta,
        near_poor_total=latest_near_poor,
        near_poor_delta_percent=near_poor_delta,
        exit_poverty_total=exit_poverty_total,
        at_risk_total=None,
        at_risk_note=None,
    )
