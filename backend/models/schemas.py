from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Health ──

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: datetime


# ── Forecast ──

class HourlyForecast(BaseModel):
    timestamp: datetime
    aqi: float
    pm25: float
    pm10: float
    aqi_low: float = Field(description="10th percentile bound")
    aqi_high: float = Field(description="90th percentile bound")


class WardForecastSummary(BaseModel):
    ward_id: str
    ward_name: str
    lat: float
    lon: float
    current_aqi: float
    forecast_aqi_24h: float
    forecast_aqi_48h: float
    forecast_aqi_72h: float
    trend: str = Field(description="improving / stable / worsening")
    cigarette_equivalent: float


class CityForecastResponse(BaseModel):
    city: str
    generated_at: datetime
    total_wards: int
    city_avg_aqi: float
    worst_ward: str
    best_ward: str
    wards: list[WardForecastSummary]


class WardForecastDetailResponse(BaseModel):
    ward_id: str
    ward_name: str
    city: str
    generated_at: datetime
    current_aqi: float
    current_pm25: float
    cigarette_equivalent: float
    hourly: list[HourlyForecast]


# ── Blame (SHAP) ──

class BlameFactor(BaseModel):
    name: str
    icon: str
    percentage: float = Field(description="Contribution 0-100")
    shap_value: float


class BlameResponse(BaseModel):
    ward_id: str
    ward_name: str
    current_aqi: float
    factors: list[BlameFactor]
    explanation: str
    forecast_trend: str = Field(description="improving / stable / worsening")


# ── Enforcement ──

class EnforcementTicket(BaseModel):
    ticket_id: str
    ward_id: str
    ward_name: str
    urgency: str = Field(description="HIGH / MEDIUM / LOW")
    current_aqi: float
    primary_cause: str
    primary_cause_icon: str
    primary_cause_percentage: float
    recommended_action: str
    estimated_aqi_reduction: str
    estimated_aqi_reduction_pct: Optional[float] = None
    intervention_action: Optional[str] = None
    affected_population: Optional[int] = Field(None, description="Population of the ward containing the station; null if unknown")
    schools_in_zone: Optional[int] = Field(None, description="Verified schools in that ward; null if unknown")
    hospitals_in_zone: Optional[int] = Field(None, description="Verified hospitals in that ward; null if unknown")
    generated_at: datetime


class EnforcementResponse(BaseModel):
    city: str
    impact_data_note: Optional[str] = None
    total_tickets: int
    high_urgency_count: int
    wards_affected: int
    tickets: list[EnforcementTicket]


# ── Chat ──

class ChatRequest(BaseModel):
    message: str
    language: str = Field(default="en", description="en / hi")
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    language: str
    conversation_id: str
    sources: list[str] = Field(default_factory=list)


# ── Vulnerable Locations ──

class VulnerableLocation(BaseModel):
    name: str
    type: str = Field(description="hospital / school / elderly_care")
    lat: float
    lon: float
    ward_id: str
    ward_name: str
    source: str = Field("unknown", description="osm / synthetic-demo / unknown")
    verified: bool = Field(False, description="True only for real OpenStreetMap records")


class VulnerableResponse(BaseModel):
    city: str
    total_locations: int
    verified_locations: int = 0
    data_note: Optional[str] = None
    locations: list[VulnerableLocation]


# ── What-If ──

class WhatIfRequest(BaseModel):
    ward_id: str
    intervention: str = Field(description="e.g. pause_construction, restrict_traffic")
    duration_hours: int = Field(default=48)


class WhatIfResponse(BaseModel):
    ward_id: str
    ward_name: str
    intervention: str
    duration_hours: int
    current_forecast: float
    with_intervention: float
    reduction: float
    reduction_percentage: float
