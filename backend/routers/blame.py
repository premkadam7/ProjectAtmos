from fastapi import APIRouter, Depends, HTTPException
from routers.validation import supported_city
from models.forecaster import get_ward_blame

router = APIRouter(prefix="/api/blame", tags=["blame"])

@router.get("/{city}/{ward_id}")
def get_blame_score(ward_id: str, city: str = Depends(supported_city)):
    blame_data = get_ward_blame(ward_id)
    if not blame_data:
        raise HTTPException(status_code=404, detail=f"No data for ward: {ward_id}")

    blame_data["city"] = city
    return blame_data
