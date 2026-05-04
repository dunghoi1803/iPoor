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
from ..constants import PovertyStatus, Roles

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


def ensure_dashboard_aggregates(db: Session, force: bool = False) -> int:
    latest_year_row = db.query(models.HouseholdSurvey.survey_year).order_by(desc(models.HouseholdSurvey.survey_year)).first()
    latest_year = latest_year_row[0] if latest_year_row else datetime.now().year
    years = sorted([latest_year - i for i in range(5)])

    existing_count = db.query(func.count(models.DashboardAggregate.id)).filter(
        models.DashboardAggregate.survey_year.in_(years)
    ).scalar() or 0
    if existing_count > 0 and not force:
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


def apply_scope_filter(query, scope: str, name: str | None):
    if scope == SCOPE_COUNTRY:
        return query
    if scope == SCOPE_REGION and name:
        return query.filter(models.HouseholdRiskScore.scope_region == name)
    if scope == SCOPE_PROVINCE and name:
        return query.filter(models.HouseholdRiskScore.scope_province == name)
    return query


def enforce_scope_permission(scope: str, name: str | None, current_user: models.User) -> tuple[str, str | None]:
    if current_user.role == Roles.ADMIN:
        return scope, name
    if current_user.role == Roles.PROVINCE_OFFICER:
        return SCOPE_PROVINCE, current_user.province
    if current_user.role == Roles.DISTRICT_OFFICER:
        return SCOPE_PROVINCE, current_user.province
    if current_user.role == Roles.COMMUNE_OFFICER:
        return SCOPE_PROVINCE, current_user.province
    return scope, name


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


@router.get("/risk-summary", response_model=schemas.DashboardRiskSummary)
def get_dashboard_risk_summary(
    scope: str = Query(SCOPE_COUNTRY),
    name: str | None = Query(None),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardRiskSummary:
    scope, name = enforce_scope_permission(scope, name, current_user)
    latest_target_row = db.query(models.HouseholdRiskScore.predicted_for_year).order_by(
        desc(models.HouseholdRiskScore.predicted_for_year)
    ).first()
    if not latest_target_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chưa có dữ liệu dự báo rủi ro. Vui lòng chạy pipeline train/predict trước.",
        )

    predicted_for_year = int(latest_target_row[0])
    scoped = apply_scope_filter(
        db.query(models.HouseholdRiskScore).filter(models.HouseholdRiskScore.predicted_for_year == predicted_for_year),
        scope,
        name,
    )

    # Get all aggregates in single query
    agg = scoped.with_entities(
        func.avg(models.HouseholdRiskScore.risk_score).label("avg_score"),
        func.count(models.HouseholdRiskScore.id).label("total"),
    ).first()

    high_risk_count = scoped.filter(models.HouseholdRiskScore.risk_band == "high").count()
    medium_risk_count = scoped.filter(models.HouseholdRiskScore.risk_band == "medium").count()
    low_risk_count = scoped.filter(models.HouseholdRiskScore.risk_band == "low").count()

    # Check if no data for this scope
    total_count = int(agg.total) if agg else 0
    if total_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không có dữ liệu dự báo cho địa bàn {name or 'toàn quốc'}. Kiểm tra quyền truy cập hoặc liên hệ quản trị viên.",
        )

    model_info = scoped.with_entities(
        models.HouseholdRiskScore.model_name,
        models.HouseholdRiskScore.model_version,
    ).first()

    avg_score = float(agg.avg_score) if agg and agg.avg_score else 0.0
    model_name = model_info.model_name if model_info else None
    model_version = model_info.model_version if model_info else None

    scope_name = SCOPE_ALL
    if scope != SCOPE_COUNTRY and name:
        scope_name = name

    # Query reasons, with fallback to country if scope has no reasons
    reason_rows = db.query(models.RiskReasonAggregate).filter(
        and_(
            models.RiskReasonAggregate.scope_type == scope,
            models.RiskReasonAggregate.scope_name == scope_name,
            models.RiskReasonAggregate.predicted_for_year == predicted_for_year,
        )
    ).order_by(desc(models.RiskReasonAggregate.importance)).limit(5).all()

    # If no reasons for this scope, fallback to country
    if not reason_rows and scope != SCOPE_COUNTRY:
        reason_rows = db.query(models.RiskReasonAggregate).filter(
            and_(
                models.RiskReasonAggregate.scope_type == SCOPE_COUNTRY,
                models.RiskReasonAggregate.scope_name == SCOPE_ALL,
                models.RiskReasonAggregate.predicted_for_year == predicted_for_year,
            )
        ).order_by(desc(models.RiskReasonAggregate.importance)).limit(5).all()

    trend_rows = []
    for year in range(predicted_for_year - 4, predicted_for_year + 1):
        year_scoped = apply_scope_filter(
            db.query(models.HouseholdRiskScore).filter(models.HouseholdRiskScore.predicted_for_year == year),
            scope,
            name,
        )
        agg = year_scoped.with_entities(
            func.avg(models.HouseholdRiskScore.risk_score).label("avg"),
            func.count(models.HouseholdRiskScore.id).label("total"),
        ).first()
        high_count = year_scoped.filter(models.HouseholdRiskScore.risk_band == "high").count()
        if not agg or agg.total == 0:
            continue
        trend_rows.append(
            schemas.RiskYearPoint(
                year=year,
                avg_score=round(float(agg.avg) if agg.avg else 0.0, 4),
                high_risk_households=high_count,
            )
        )

    return schemas.DashboardRiskSummary(
        predicted_for_year=predicted_for_year,
        scope=scope,
        scope_name=scope_name,
        algo_name=model_name or "xgboost",
        algo_version=model_version or "unknown",
        avg_risk_score=round(avg_score, 4),
        high_risk_households=high_risk_count,
        medium_risk_households=medium_risk_count,
        low_risk_households=low_risk_count,
        total_households=total_count,
        top_reasons=[
            schemas.RiskReasonItem(
                key=row.reason_key,
                label=row.reason_label,
                importance=float(row.importance),
                affected_households=int(row.affected_households),
            )
            for row in reason_rows
        ],
        trend=trend_rows,
    )


@router.get("/risk-households", response_model=schemas.DashboardRiskHouseholdList)
def get_dashboard_risk_households(
    scope: str = Query(SCOPE_COUNTRY),
    name: str | None = Query(None),
    risk_band: str = Query("high"),
    predicted_for_year: int | None = Query(None),
    skip: int = 0,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> schemas.DashboardRiskHouseholdList:
    scope, name = enforce_scope_permission(scope, name, current_user)

    target_year = predicted_for_year
    if target_year is None:
        latest_target_row = db.query(models.HouseholdRiskScore.predicted_for_year).order_by(
            desc(models.HouseholdRiskScore.predicted_for_year)
        ).first()
        if not latest_target_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chưa có dữ liệu dự báo")
        target_year = int(latest_target_row[0])

    query = db.query(
        models.HouseholdRiskScore,
        models.Household,
    ).join(
        models.Household,
        models.Household.id == models.HouseholdRiskScore.household_id,
    ).filter(
        models.HouseholdRiskScore.predicted_for_year == target_year,
        models.HouseholdRiskScore.risk_band == risk_band,
    )
    query = apply_scope_filter(query, scope, name)

    total = query.count()
    rows = query.order_by(models.HouseholdRiskScore.risk_score.desc()).offset(skip).limit(limit).all()
    if rows:
        algo_name = rows[0][0].model_name
        algo_version = rows[0][0].model_version
    else:
        algo_name = "xgboost"
        algo_version = "n/a"

    scope_name = SCOPE_ALL
    if scope != SCOPE_COUNTRY and name:
        scope_name = name

    return schemas.DashboardRiskHouseholdList(
        predicted_for_year=target_year,
        scope=scope,
        scope_name=scope_name,
        algo_name=algo_name,
        algo_version=algo_version,
        total=total,
        items=[
            schemas.RiskHouseholdItem(
                household_id=household.id,
                household_code=household.household_code,
                head_name=household.head_name,
                province=household.province,
                district=household.district,
                commune=household.commune,
                risk_score=float(score.risk_score),
                risk_band=score.risk_band,
            )
            for score, household in rows
        ],
    )
