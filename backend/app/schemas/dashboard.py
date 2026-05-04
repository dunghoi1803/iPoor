from pydantic import BaseModel


class DashboardSeries(BaseModel):
    years: list[int]
    poor: list[float]
    near_poor: list[float]
    exit_poverty: list[float]


class DashboardRegionItem(BaseModel):
    label: str
    value: float


class DashboardSummary(BaseModel):
    latest_year: int
    poor_total: float
    poor_delta_percent: float
    near_poor_total: float
    near_poor_delta_percent: float
    exit_poverty_total: float
    series: DashboardSeries
    top_regions: list[DashboardRegionItem]


class DashboardTrendOptions(BaseModel):
    regions: list[str]
    provinces: list[str]


class DashboardKpis(BaseModel):
    latest_year: int
    poor_total: float
    poor_delta_percent: float
    near_poor_total: float
    near_poor_delta_percent: float
    exit_poverty_total: float


class DashboardOverview(BaseModel):
    latest_year: int
    filters: DashboardTrendOptions
    kpis: DashboardKpis
    trend: DashboardSeries
    regions: list[DashboardRegionItem]


class RiskReasonItem(BaseModel):
    key: str
    label: str
    importance: float
    affected_households: int


class RiskYearPoint(BaseModel):
    year: int
    avg_score: float
    high_risk_households: int


class DashboardRiskSummary(BaseModel):
    predicted_for_year: int
    scope: str
    scope_name: str
    algo_name: str
    algo_version: str
    avg_risk_score: float
    high_risk_households: int
    medium_risk_households: int
    low_risk_households: int
    total_households: int
    top_reasons: list[RiskReasonItem]
    trend: list[RiskYearPoint]


class RiskHouseholdItem(BaseModel):
    household_id: int
    household_code: str
    head_name: str
    province: str
    district: str
    commune: str
    risk_score: float
    risk_band: str


class DashboardRiskHouseholdList(BaseModel):
    predicted_for_year: int
    scope: str
    scope_name: str
    algo_name: str
    algo_version: str
    total: int
    items: list[RiskHouseholdItem]
