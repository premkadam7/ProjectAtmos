from fastapi import APIRouter, HTTPException
from models.schemas import WhatIfRequest, WhatIfResponse
from models.forecaster import run_whatif_simulation

router = APIRouter(prefix="/api/whatif", tags=["whatif"])

@router.post("", response_model=WhatIfResponse)
def post_whatif(request: WhatIfRequest):
    if request.duration_hours <= 0:
        raise HTTPException(status_code=422, detail="duration_hours must be positive")
    
    res = run_whatif_simulation(
        ward_id=request.ward_id,
        intervention=request.intervention,
        duration_hours=request.duration_hours
    )
    
    return res
