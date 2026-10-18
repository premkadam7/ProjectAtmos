from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone
from routers.validation import supported_city
from models.forecaster import get_city_overview, get_city_hourly, get_ward_forecast, get_data_source

router = APIRouter(prefix="/api/forecast", tags=["forecast"])

@router.get("/{city}")
def get_city_forecast(city: str = Depends(supported_city)):
    overview = get_city_overview()
    if not overview:
        raise HTTPException(status_code=503, detail="Forecast data is not available yet.")

    aqi_values = [w["current_aqi"] for w in overview]
    worst = max(overview, key=lambda w: w["current_aqi"])
    best = min(overview, key=lambda w: w["current_aqi"])

    return {
        "city": city,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **get_data_source(),
        "total_wards": len(overview),
        "city_avg_aqi": round(sum(aqi_values) / len(aqi_values), 1),
        "worst_ward": worst["ward_id"],
        "best_ward": best["ward_id"],
        "wards": overview,
    }

@router.get("/{city}/timeline")
def get_city_timeline(city: str = Depends(supported_city)):
    """Hourly predicted AQI for every ward over the forecast horizon (drives the map time slider)."""
    return {"city": city, **get_data_source(), **get_city_hourly()}

@router.get("/{city}/{ward_id}")
def get_ward_forecast_endpoint(ward_id: str, city: str = Depends(supported_city), hours: int = Query(72, ge=1, le=72)):
    forecast_data = get_ward_forecast(ward_id, hours)

    return {
        "ward_id": forecast_data["ward_id"],
        "ward_name": forecast_data["ward_name"],
        "city": city,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **get_data_source(),
        "current_aqi": forecast_data["current_aqi"],
        "current_pm25": forecast_data["current_pm25"],
        "cigarette_equivalent": forecast_data["cigarette_equivalent"],
        "hourly": forecast_data["hourly"],
    }
