from fastapi import APIRouter, HTTPException
from models.forecaster import get_ward_blame

router = APIRouter(prefix="/api/blame", tags=["blame"])

@router.get("/{city}/{ward_id}")
def get_blame_score(city: str, ward_id: str):
    blame_data = get_ward_blame(ward_id)
    if not blame_data:
        raise HTTPException(status_code=404, detail=f"No data for ward: {ward_id}")

    blame_data["city"] = city
    return blame_data
