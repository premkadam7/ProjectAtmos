from fastapi import APIRouter, Query
from datetime import datetime, timezone
from models.forecaster import get_city_overview, get_ward_forecast

router = APIRouter(prefix="/api/forecast", tags=["forecast"])

@router.get("/{city}")
def get_city_forecast(city: str):
    overview = get_city_overview()
    if not overview:
        return {"error": "Data not available."}

    aqi_values = [w["current_aqi"] for w in overview]
    worst = max(overview, key=lambda w: w["current_aqi"])
    best = min(overview, key=lambda w: w["current_aqi"])

    return {
        "city": city,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_wards": len(overview),
        "city_avg_aqi": round(sum(aqi_values) / len(aqi_values), 1),
        "worst_ward": worst["ward_id"],
        "best_ward": best["ward_id"],
        "wards": overview,
    }

@router.get("/{city}/{ward_id}")
def get_ward_forecast_endpoint(city: str, ward_id: str, hours: int = Query(72, ge=1, le=72)):
    forecast_data = get_ward_forecast(ward_id, hours)
    if not forecast_data:
        return {"error": f"Ward {ward_id} not found."}

    return {
        "ward_id": forecast_data["ward_id"],
        "ward_name": forecast_data["ward_name"],
        "city": city,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_aqi": forecast_data["current_aqi"],
        "current_pm25": round(forecast_data["current_aqi"] / 2.0, 1),
        "cigarette_equivalent": forecast_data["cigarette_equivalent"],
        "hourly": forecast_data["hourly"],
    }
