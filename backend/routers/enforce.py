from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone
import uuid
from models.forecaster import get_city_overview, get_ward_blame, run_whatif_simulation
import os
import json
import pandas as pd

_pop_data = None
_vuln_data = None

def _load_data():
    global _pop_data, _vuln_data
    if _pop_data is None:
        try:
            df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data_store", "cache", "delhi_wards_population.csv"))
            _pop_data = {str(row["ward_name"]).upper(): row["population"] for _, row in df.iterrows() if not pd.isna(row["population"])}
        except:
            _pop_data = {}
    if _vuln_data is None:
        try:
            with open(os.path.join(os.path.dirname(__file__), "..", "data_store", "geojson", "vulnerable_locations.geojson")) as f:
                _vuln_data = json.load(f).get("features", [])
        except:
            _vuln_data = []

router = APIRouter(prefix="/api/enforce", tags=["enforcement"])

RECOMMENDATIONS = {
    "Traffic & Time": "Implement localized traffic diversions and odd-even scheme on arterial roads.",
    "Weather": "Increase mechanised sweeping and water sprinkling along key corridors.",
    "Historical / Baseline": "Inspect and penalize local industrial and construction sites in the vicinity.",
    "Geography & Infra": "Launch targeted afforestation drives and regulate localized dense-population emissions.",
}

@router.get("/{city}")
def get_enforcement_tickets(
    city: str,
    source: Optional[str] = Query(None, description="Filter by primary cause")
):
    _load_data()
    overview = get_city_overview()
    if not overview:
        return {"error": "No forecast data available"}

    worst_wards = sorted(overview, key=lambda x: x["current_aqi"], reverse=True)

    tickets = []
    for w in worst_wards[:5]:
        if w["current_aqi"] < 100:
            continue

        blame = get_ward_blame(w["ward_id"])
        if not blame or not blame.get("factors"):
            continue

        top_factor = blame["factors"][0]
        cause = top_factor["name"]

        if source and source.lower() not in cause.lower():
            continue

        if w["current_aqi"] > 300:
            urgency = "HIGH"
        elif w["current_aqi"] >= 200:
            urgency = "MEDIUM"
        else:
            urgency = "LOW"

        ward_name_upper = w["ward_name"].upper()
        pop = _pop_data.get(ward_name_upper, 50000)
        
        schools = sum(1 for v in _vuln_data if v.get("properties", {}).get("ward_name", "").upper() == ward_name_upper and v.get("properties", {}).get("type") == "school")
        hospitals = sum(1 for v in _vuln_data if v.get("properties", {}).get("ward_name", "").upper() == ward_name_upper and v.get("properties", {}).get("type") == "hospital")

        cause_to_intervention = {
            "Traffic & Time": "restrict_traffic",
            "Historical / Baseline": "industrial_shutdown",
            "Geography & Infra": "pause_construction",
            "Weather": "restrict_traffic",
        }
        intervention = cause_to_intervention.get(cause, "restrict_traffic")
        
        whatif_res = run_whatif_simulation(w["ward_id"], intervention, duration_hours=48)
        reduction_pct = whatif_res.get("reduction_percentage", 0.0)

        tickets.append({
            "ticket_id": f"TCK-{uuid.uuid4().hex[:6].upper()}",
            "ward_id": w["ward_id"],
            "ward_name": w["ward_name"],
            "urgency": urgency,
            "current_aqi": w["current_aqi"],
            "primary_cause": cause,
            "primary_cause_icon": top_factor["icon"],
            "primary_cause_percentage": top_factor["percentage"],
            "recommended_action": RECOMMENDATIONS.get(
                cause, "Deploy mobile monitoring vans to identify point-source emissions."
            ),
            "estimated_aqi_reduction": f"{reduction_pct:.1f}%",
            "estimated_aqi_reduction_pct": reduction_pct,
            "intervention_action": intervention.replace("_", " ").title(),
            "affected_population": int(pop),
            "schools_in_zone": schools,
            "hospitals_in_zone": hospitals,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    return {
        "city": city,
        "total_tickets": len(tickets),
        "high_urgency_count": sum(1 for t in tickets if t["urgency"] == "HIGH"),
        "wards_affected": len(tickets),
        "tickets": tickets,
    }
