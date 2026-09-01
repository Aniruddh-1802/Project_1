from datetime import datetime

from pydantic import BaseModel,Field

from typing import Optional


class NetworkSummaryResponse(
    BaseModel
):
    total_activity: float

    active_grids: int

    peak_hour: int

    top_grid: int

    as_of: datetime


class GridActivityPoint(BaseModel):

    timestamp: datetime

    sms_activity: float

    call_activity: float

    internet_activity: float

    total_activity: float


class GridActivityResponse(BaseModel):

    grid_id: int

    as_of: datetime

    interval_count: int

    activity: list[GridActivityPoint]



class HotspotItem(BaseModel):

    grid_id: int

    timestamp: datetime

    total_activity: float

    sms_activity: float

    call_activity: float

    internet_activity: float

    status: str

    reason: str

    # Future ML fields

    risk_score: Optional[float] = None

    risk_level: Optional[str] = None

    model_version: Optional[str] = None


class HotspotResponse(BaseModel):

    as_of: datetime

    count: int

    hotspots: list[HotspotItem]


class AlertItem(BaseModel):

    grid_id: int

    timestamp: datetime

    severity: str

    total_activity: float

    sms_activity: float

    call_activity: float

    internet_activity: float

    reason: str

    status: str

    # Future ML fields

    risk_score: Optional[float] = None

    risk_level: Optional[str] = None

    model_version: Optional[str] = None


class AlertResponse(BaseModel):

    as_of: datetime

    count: int

    alerts: list[AlertItem]



class GridFeaturesResponse(BaseModel):

    grid_id: int

    avg_activity: float

    activity_growth: float

    active_hours: int

    peak_ratio: float

    variability: float

    internet_share: float

    feature_timestamp: datetime

    data_quality_status: str

    feature_freshness_hours: float



class RiskPredictionRequest(BaseModel):

    avg_activity: float

    activity_growth: float

    active_hours: int = Field(
        ge=0
    )

    peak_ratio: float

    variability: float

    internet_share: float = Field(
        ge=0,
        le=1
    )


class RiskPredictionResponse(BaseModel):

    risk_score: float

    risk_level: str

    model_version: str

    explanation_note: str