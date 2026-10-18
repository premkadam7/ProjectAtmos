from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone
import uuid
from models.forecaster import get_city_overview, get_ward_blame, run_whatif_simulation
from services.places import reference_data, ward_facility_count, ward_population

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

        # Joined on the canonical id of the ward polygon containing the
        # station; None means the figure is unknown, not zero.
        pop = ward_population(w["ward_id"])
        schools = ward_facility_count(w["ward_id"], "school")
        hospitals = ward_facility_count(w["ward_id"], "hospital")

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
            "affected_population": pop,
            "schools_in_zone": schools,
            "hospitals_in_zone": hospitals,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    ref = reference_data()
    return {
        "city": city,
        "impact_data_note": (
            "Population and facility counts are for the municipal ward containing each monitoring station. "
            "Missing population figures are reported as unknown. "
            + ("Facility counts use verified OpenStreetMap records only."
               if ref["facilities_verified"] else
               "No verified facility data is available, so school and hospital counts are unknown.")
        ),
        "total_tickets": len(tickets),
        "high_urgency_count": sum(1 for t in tickets if t["urgency"] == "HIGH"),
        "wards_affected": len(tickets),
        "tickets": tickets,
    }
