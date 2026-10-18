import os
import json
from fastapi import APIRouter, Depends, HTTPException
from routers.validation import supported_city
from models.schemas import VulnerableResponse, VulnerableLocation
from services.places import is_verified

router = APIRouter(prefix="/api/vulnerable", tags=["vulnerable"])

GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data_store", "geojson", "vulnerable_locations.geojson")

@router.get("/{city}", response_model=VulnerableResponse)
def get_vulnerable_locations(city: str = Depends(supported_city)):
    if not os.path.exists(GEOJSON_PATH):
        try:
            from data.fetch_vulnerable import main as fetch_main
            fetch_main()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate vulnerable locations data: {str(e)}"
            )
            
    if not os.path.exists(GEOJSON_PATH):
        raise HTTPException(
            status_code=404,
            detail="Vulnerable locations GeoJSON cache file not found."
        )
        
    try:
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read vulnerable locations data: {str(e)}"
        )
        
    locations = []
    features = geojson_data.get("features", [])
    for feature in features:
        geom = feature.get("geometry", {})
        props = feature.get("properties", {})
        
        coordinates = geom.get("coordinates", [])
        if len(coordinates) >= 2:
            lon = coordinates[0]
            lat = coordinates[1]
            
            locations.append(
                VulnerableLocation(
                    name=props.get("name", "Unknown"),
                    type=props.get("type", "school"),
                    lat=lat,
                    lon=lon,
                    ward_id=props.get("ward_id", "Unknown"),
                    ward_name=props.get("ward_name", "Unknown"),
                    source="synthetic-demo" if props.get("synthetic") else props.get("source", "unknown"),
                    verified=is_verified(props),
                )
            )
            
    verified = sum(1 for loc in locations if loc.verified)
    if verified == len(locations):
        note = None
    elif verified == 0:
        note = "These are synthetic placeholder locations, not real facilities."
    else:
        note = f"{len(locations) - verified} of {len(locations)} locations are synthetic placeholders."
    return VulnerableResponse(
        city=city,
        total_locations=len(locations),
        verified_locations=verified,
        data_note=note,
        locations=locations
    )
