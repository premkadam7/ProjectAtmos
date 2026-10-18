from typing import Optional
from fastapi import APIRouter, Depends, Query
from routers.validation import supported_city
from models.forecaster import HISTORY_SERIES_INFO, get_history, get_data_source

router = APIRouter(prefix="/api/history", tags=["history"])

@router.get("/{city}")
def get_city_history(
    city: str = Depends(supported_city),
    ward_id: Optional[str] = None,
    hours: int = Query(24 * 30, ge=1, le=24 * 31),
):
    """Hourly modelled pollutant history (µg/m³) and PM2.5-based AQI, city mean or for one ward."""
    return {
        "city": city,
        "ward_id": ward_id,
        **get_data_source(),
        "series_kind": HISTORY_SERIES_INFO["kind"],
        "series_description": HISTORY_SERIES_INFO["description"],
        "units": {"pm25": "µg/m³", "pm10": "µg/m³", "co": "µg/m³", "no2": "µg/m³", "so2": "µg/m³", "o3": "µg/m³"},
        "series": get_history(ward_id, hours),
    }
