from collections import defaultdict
import csv
from datetime import datetime
from functools import lru_cache
import io
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote
from unicodedata import normalize

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, delete, desc, func
from sqlalchemy.orm import Session

from .. import deps, models, schemas
from ..constants import PovertyStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

SCOPE_COUNTRY = "country"
SCOPE_REGION = "region"
SCOPE_PROVINCE = "province"

SCOPE_ALL = "all"


@lru_cache(maxsize=1)
def get_region_map() -> dict[str, str]:
    try:
        here = Path(__file__).resolve()
        path = here.parents[2] / "FE" / "data" / "processed" / "region_map.json"
        if path.exists():
            with path.open(encoding="utf-8") as h:
                data = json.load(h)
                return data.get("province_to_region", {})
    except Exception:
        pass
    return {}


def build_region_buckets(region_map: dict[str, str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for province, region in region_map.items():
        buckets[region].append(province)
    return buckets

def calculate_percent_change(current: float, previous: float) -> float:
    if not previous:
        return 0.0
    return ((current - previous) / previous) * 100


def ensure_dashboard_aggregates(db: Session) -> int:
    latest_year_row = db.query(models.HouseholdSurvey.survey_year).order_by(desc(models.HouseholdSurvey.survey_year)).first()
    latest_year = latest_year_row[0] if latest_year_row else datetime.now().year
    years = sorted([latest_year - i for i in range(5)])

    existing_count = db.query(func.count(models.DashboardAggregate.id)).filter(
        models.DashboardAggregate.survey_year.in_(years)
    ).scalar() or 0
    if existing_count > 0:
        return latest_year

    region_map = get_region_map()

    country_rows = db.query(
        models.HouseholdSurvey.survey_year,
        models.HouseholdSurvey.poverty_status,
        func.count(models.HouseholdSurvey.id),
    ).filter(models.HouseholdSurvey.survey_year.in_(years)).group_by(
        models.HouseholdSurvey.survey_year,
        models.HouseholdSurvey.poverty_status,
    ).all()

    province_rows = db.query(
        models.Household.province,
        models.HouseholdSurvey.survey_year,
        models.HouseholdSurvey.poverty_status,
        func.count(models.HouseholdSurvey.id),
    ).join(models.HouseholdSurvey).filter(
        models.HouseholdSurvey.survey_year.in_(years)
    ).group_by(
        models.Household.province,
        models.HouseholdSurvey.survey_year,
        models.HouseholdSurvey.poverty_status,
    ).all()

    db.execute(delete(models.DashboardAggregate).where(models.DashboardAggregate.survey_year.in_(years)))

    inserts: list[models.DashboardAggregate] = []
    for year, poverty_status, count in country_rows:
        inserts.append(models.DashboardAggregate(
            scope_type=SCOPE_COUNTRY,
            scope_name=SCOPE_ALL,
            survey_year=year,
            poverty_status=poverty_status,
            household_count=count,
        ))

    region_acc: dict[tuple[str, int, Any], int] = defaultdict(int)
    for province, year, poverty_status, count in province_rows:
        inserts.append(models.DashboardAggregate(
            scope_type=SCOPE_PROVINCE,
            scope_name=province,
            survey_year=year,
            poverty_status=poverty_status,
            household_count=count,
        ))
        region_name = region_map.get(province, "Khác")
        region_acc[(region_name, year, poverty_status)] += count

    for (region_name, year, poverty_status), count in region_acc.items():
        inserts.append(models.DashboardAggregate(
            scope_type=SCOPE_REGION,
            scope_name=region_name,
            survey_year=year,
            poverty_status=poverty_status,
            household_count=count,
        ))

    if inserts:
        db.bulk_save_objects(inserts)
        db.commit()

    return latest_year


def resolve_scope(scope: str, name: str | None) -> tuple[str, str]:
    if scope == SCOPE_COUNTRY:
        return SCOPE_COUNTRY, SCOPE_ALL
    if name:
        return scope, name
    return SCOPE_COUNTRY, SCOPE_ALL


def aggregate_rows_for_scope(db: Session, scope: str, name: str | None, years: list[int]):
    scope_type, scope_name = resolve_scope(scope, name)
    return db.query(
        models.DashboardAggregate.survey_year,
        models.DashboardAggregate.poverty_status,
        models.DashboardAggregate.household_count,
    ).filter(
        and_(
            models.DashboardAggregate.scope_type == scope_type,
            models.DashboardAggregate.scope_name == scope_name,
            models.DashboardAggregate.survey_year.in_(years),
        )
    ).all()


def build_stats_map(rows: list[tuple[int, Any, int]]) -> dict[int, dict[Any, int]]:
    stats_map: dict[int, dict[Any, int]] = defaultdict(lambda: defaultdict(int))
    for year, status, count in rows:
        stats_map[year][status] = count
    return stats_map


def slugify_ascii(value: str) -> str:
    text = normalize("NFKD", value)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "unknown"

@router.get("/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardSummary:
    latest_year = ensure_dashboard_aggregates(db)
    years = sorted([latest_year - i for i in range(5)])
    counts_raw = aggregate_rows_for_scope(db, SCOPE_COUNTRY, None, years)
    stats_map = build_stats_map(counts_raw)

    # 3. Build Trend Series
    series_poor = []
    series_near_poor = []
    series_exit = []

    for y in years:
        y_data = stats_map[y]
        series_poor.append(float(y_data.get(PovertyStatus.POOR, 0)))
        series_near_poor.append(float(y_data.get(PovertyStatus.NEAR_POOR, 0)))
        series_exit.append(float(y_data.get(PovertyStatus.ESCAPED, 0)))

    region_rows = db.query(
        models.DashboardAggregate.scope_name,
        models.DashboardAggregate.household_count,
    ).filter(
        and_(
            models.DashboardAggregate.scope_type == SCOPE_REGION,
            models.DashboardAggregate.survey_year == latest_year,
            models.DashboardAggregate.poverty_status == PovertyStatus.POOR,
        )
    ).all()
    top_regions = [
        schemas.DashboardRegionItem(label=label, value=float(value))
        for label, value in sorted(region_rows, key=lambda item: item[1], reverse=True)
    ]

    latest_year_data = stats_map[latest_year]
    prev_year_data = stats_map[latest_year - 1]

    return schemas.DashboardSummary(
        latest_year=latest_year,
        poor_total=float(latest_year_data.get(PovertyStatus.POOR, 0)),
        poor_delta_percent=calculate_percent_change(latest_year_data.get(PovertyStatus.POOR, 0), prev_year_data.get(PovertyStatus.POOR, 0)),
        near_poor_total=float(latest_year_data.get(PovertyStatus.NEAR_POOR, 0)),
        near_poor_delta_percent=calculate_percent_change(latest_year_data.get(PovertyStatus.NEAR_POOR, 0), prev_year_data.get(PovertyStatus.NEAR_POOR, 0)),
        exit_poverty_total=float(latest_year_data.get(PovertyStatus.ESCAPED, 0)),
        series=schemas.DashboardSeries(
            years=years,
            poor=series_poor,
            near_poor=series_near_poor,
            exit_poverty=series_exit,
        ),
        top_regions=top_regions
    )

@router.get("/filters", response_model=schemas.DashboardTrendOptions)
def get_dashboard_filters(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardTrendOptions:
    ensure_dashboard_aggregates(db)
    region_map = get_region_map()
    regions = sorted(list(set(region_map.values())))
    provinces = [r[0] for r in db.query(models.Household.province).distinct().all()]
    return schemas.DashboardTrendOptions(regions=regions, provinces=sorted(provinces))

@router.get("/kpis", response_model=schemas.DashboardKpis)
def get_dashboard_kpis(
    scope: str = Query(SCOPE_COUNTRY),
    name: str | None = Query(None),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardKpis:
    latest_year = ensure_dashboard_aggregates(db)
    counts_raw = aggregate_rows_for_scope(db, scope, name, [latest_year, latest_year - 1])
    stats_map = build_stats_map(counts_raw)

    l_poor = stats_map[latest_year].get(PovertyStatus.POOR, 0)
    l_near = stats_map[latest_year].get(PovertyStatus.NEAR_POOR, 0)
    p_poor = stats_map[latest_year - 1].get(PovertyStatus.POOR, 0)
    p_near = stats_map[latest_year - 1].get(PovertyStatus.NEAR_POOR, 0)

    return schemas.DashboardKpis(
        latest_year=latest_year,
        poor_total=float(l_poor),
        poor_delta_percent=calculate_percent_change(l_poor, p_poor),
        near_poor_total=float(l_near),
        near_poor_delta_percent=calculate_percent_change(l_near, p_near),
        exit_poverty_total=float(stats_map[latest_year].get(PovertyStatus.ESCAPED, 0)),
    )

@router.get("/trend", response_model=schemas.DashboardSeries)
def get_dashboard_trend(
    scope: str = Query(SCOPE_COUNTRY),
    name: str | None = Query(None),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardSeries:
    latest_year = ensure_dashboard_aggregates(db)
    years = sorted([latest_year - i for i in range(5)])
    counts_raw = aggregate_rows_for_scope(db, scope, name, years)
    stats_map = build_stats_map(counts_raw)

    poor, near_poor, escaped = [], [], []
    for y in years:
        poor.append(float(stats_map[y].get(PovertyStatus.POOR, 0)))
        near_poor.append(float(stats_map[y].get(PovertyStatus.NEAR_POOR, 0)))
        escaped.append(float(stats_map[y].get(PovertyStatus.ESCAPED, 0)))

    return schemas.DashboardSeries(
        years=years,
        poor=poor,
        near_poor=near_poor,
        exit_poverty=escaped
    )

@router.get("/regions", response_model=list[schemas.DashboardRegionItem])
def get_region_comparison(
    metric: str = Query("poor"),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> list[schemas.DashboardRegionItem]:
    latest_year = ensure_dashboard_aggregates(db)
    status_target = PovertyStatus.POOR if metric == "poor" else PovertyStatus.NEAR_POOR
    region_totals = db.query(
        models.DashboardAggregate.scope_name,
        models.DashboardAggregate.household_count,
    ).filter(
        and_(
            models.DashboardAggregate.scope_type == SCOPE_REGION,
            models.DashboardAggregate.survey_year == latest_year,
            models.DashboardAggregate.poverty_status == status_target,
        )
    ).all()

    return [
        schemas.DashboardRegionItem(label=r, value=float(v))
        for r, v in sorted(region_totals, key=lambda x: x[1], reverse=True)
    ]


@router.get("/overview", response_model=schemas.DashboardOverview)
def get_dashboard_overview(
    scope: str = Query(SCOPE_COUNTRY),
    name: str | None = Query(None),
    metric: str = Query("poor"),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardOverview:
    latest_year = ensure_dashboard_aggregates(db)
    years = sorted([latest_year - i for i in range(5)])
    stats_map = build_stats_map(aggregate_rows_for_scope(db, scope, name, years))

    poor = [float(stats_map[y].get(PovertyStatus.POOR, 0)) for y in years]
    near = [float(stats_map[y].get(PovertyStatus.NEAR_POOR, 0)) for y in years]
    escaped = [float(stats_map[y].get(PovertyStatus.ESCAPED, 0)) for y in years]

    l_poor = stats_map[latest_year].get(PovertyStatus.POOR, 0)
    p_poor = stats_map[latest_year - 1].get(PovertyStatus.POOR, 0)
    l_near = stats_map[latest_year].get(PovertyStatus.NEAR_POOR, 0)
    p_near = stats_map[latest_year - 1].get(PovertyStatus.NEAR_POOR, 0)

    status_target = PovertyStatus.POOR if metric == "poor" else PovertyStatus.NEAR_POOR
    regions = db.query(
        models.DashboardAggregate.scope_name,
        models.DashboardAggregate.household_count,
    ).filter(
        and_(
            models.DashboardAggregate.scope_type == SCOPE_REGION,
            models.DashboardAggregate.survey_year == latest_year,
            models.DashboardAggregate.poverty_status == status_target,
        )
    ).all()

    region_map = get_region_map()
    region_names = sorted(list(set(region_map.values())))
    provinces = [r[0] for r in db.query(models.Household.province).distinct().all()]

    return schemas.DashboardOverview(
        latest_year=latest_year,
        filters=schemas.DashboardTrendOptions(regions=region_names, provinces=sorted(provinces)),
        kpis=schemas.DashboardKpis(
            latest_year=latest_year,
            poor_total=float(l_poor),
            poor_delta_percent=calculate_percent_change(l_poor, p_poor),
            near_poor_total=float(l_near),
            near_poor_delta_percent=calculate_percent_change(l_near, p_near),
            exit_poverty_total=float(stats_map[latest_year].get(PovertyStatus.ESCAPED, 0)),
        ),
        trend=schemas.DashboardSeries(
            years=years,
            poor=poor,
            near_poor=near,
            exit_poverty=escaped,
        ),
        regions=[
            schemas.DashboardRegionItem(label=label, value=float(value))
            for label, value in sorted(regions, key=lambda x: x[1], reverse=True)
        ],
    )


@router.get("/export-households")
def export_dashboard_households(
    year: int = Query(..., ge=2000, le=3000),
    province: str = Query(SCOPE_ALL),
    poverty_status: PovertyStatus = Query(PovertyStatus.POOR),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> StreamingResponse:
    ensure_dashboard_aggregates(db)

    scope_name = SCOPE_ALL if not province else province.strip()
    if scope_name.lower() == "all":
        scope_name = SCOPE_ALL

    query = db.query(
        models.Household.household_code,
        models.Household.head_name,
        models.Household.province,
        models.Household.district,
        models.Household.commune,
        models.Household.ethnicity,
        models.HouseholdSurvey.survey_year,
        models.HouseholdSurvey.poverty_status,
        models.HouseholdSurvey.members_count,
        models.HouseholdSurvey.income_per_capita,
        models.HouseholdSurvey.survey_date,
    ).join(models.HouseholdSurvey).filter(
        and_(
            models.HouseholdSurvey.survey_year == year,
            models.HouseholdSurvey.poverty_status == poverty_status,
        )
    )

    if scope_name != SCOPE_ALL:
        query = query.filter(models.Household.province == scope_name)

    rows = query.order_by(
        models.Household.province.asc(),
        models.Household.district.asc(),
        models.Household.commune.asc(),
        models.Household.household_code.asc(),
    )

    def iter_csv():
        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.writer(output)
        writer.writerow([
            "Ma ho",
            "Chu ho",
            "Tinh",
            "Huyen",
            "Xa",
            "Dan toc",
            "Nam khao sat",
            "Trang thai",
            "So nhan khau",
            "Thu nhap binh quan",
            "Ngay khao sat",
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in rows.yield_per(2000):
            writer.writerow([
                row.household_code,
                row.head_name,
                row.province,
                row.district,
                row.commune,
                row.ethnicity or "",
                row.survey_year,
                row.poverty_status.value,
                row.members_count or "",
                row.income_per_capita or "",
                row.survey_date.isoformat() if row.survey_date else "",
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    unicode_scope = "toan-quoc" if scope_name == SCOPE_ALL else scope_name
    ascii_scope = "toan-quoc" if scope_name == SCOPE_ALL else slugify_ascii(scope_name)
    ascii_filename = f"ho-{poverty_status.value}-{ascii_scope}-{year}.csv"
    unicode_filename = f"ho-{poverty_status.value}-{unicode_scope}-{year}.csv"
    headers = {
        "Content-Disposition": (
            f"attachment; filename=\"{ascii_filename}\"; "
            f"filename*=UTF-8''{quote(unicode_filename)}"
        )
    }
    return StreamingResponse(iter_csv(), media_type="text/csv; charset=utf-8", headers=headers)
