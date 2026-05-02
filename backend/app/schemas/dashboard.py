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
