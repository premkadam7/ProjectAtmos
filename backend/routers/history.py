from typing import Optional
from fastapi import APIRouter, Query
from models.forecaster import get_history, get_data_source

router = APIRouter(prefix="/api/history", tags=["history"])

@router.get("/{city}")
def get_city_history(
    city: str,
    ward_id: Optional[str] = None,
    hours: int = Query(24 * 30, ge=1, le=24 * 31),
):
    """Observed hourly pollutant history (µg/m³) and AQI, city mean or for one ward."""
    return {
        "city": city,
        "ward_id": ward_id,
        **get_data_source(),
        "units": {"pm25": "µg/m³", "pm10": "µg/m³", "co": "µg/m³", "no2": "µg/m³", "so2": "µg/m³", "o3": "µg/m³"},
        "series": get_history(ward_id, hours),
    }
