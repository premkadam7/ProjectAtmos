import pytest
import json
from unittest.mock import patch, mock_open
from models.schemas import (
    CityForecastResponse,
    BlameResponse,
    EnforcementResponse,
    WhatIfResponse,
    ChatResponse,
    VulnerableResponse
)

# Scenario 1: Forecast-Blame-Enforce flow
def test_forecast_blame_enforce_flow(client):
    # 1. Query city forecast overview
    forecast_resp = client.get("/api/forecast/delhi")
    assert forecast_resp.status_code == 200
    forecast_data = forecast_resp.json()
    parsed_forecast = CityForecastResponse(**forecast_data)
    assert len(parsed_forecast.wards) > 0

    # Let's find the worst ward in Delhi according to the forecast
    worst_ward_id = parsed_forecast.worst_ward
    assert worst_ward_id != ""

    # 2. Query blame score for that worst ward
    blame_resp = client.get(f"/api/blame/delhi/{worst_ward_id}")
    assert blame_resp.status_code == 200
    blame_data = blame_resp.json()
    parsed_blame = BlameResponse(**blame_data)
    assert parsed_blame.ward_id == worst_ward_id
    assert len(parsed_blame.factors) > 0
    top_blame_cause = parsed_blame.factors[0].name

    # 3. Query active enforcement tickets
    enforce_resp = client.get("/api/enforce/delhi")
    assert enforce_resp.status_code == 200
    enforce_data = enforce_resp.json()
    parsed_enforce = EnforcementResponse(**enforce_data)

    # 4. Confirm ticket is generated for the worst ward with the matching primary cause
    matching_ticket = next((t for t in parsed_enforce.tickets if t.ward_id == worst_ward_id), None)
    if matching_ticket:
        assert matching_ticket.primary_cause == top_blame_cause
        assert matching_ticket.current_aqi >= 100

# Scenario 2: Enforce-WhatIf correlation
def test_enforce_whatif_correlation(client):
    # 1. Get active enforcement tickets
    enforce_resp = client.get("/api/enforce/delhi")
    assert enforce_resp.status_code == 200
    enforce_data = enforce_resp.json()
    parsed_enforce = EnforcementResponse(**enforce_data)
    assert len(parsed_enforce.tickets) > 0

    # Pick the first ticketed ward
    ticket = parsed_enforce.tickets[0]
    ward_id = ticket.ward_id
    primary_cause = ticket.primary_cause

    # Map ticket primary cause to simulator intervention
    if "traffic" in primary_cause.lower():
        intervention = "restrict_traffic"
    elif "construction" in primary_cause.lower() or "baseline" in primary_cause.lower():
        intervention = "pause_construction"
    elif "weather" in primary_cause.lower():
        intervention = "restrict_traffic"
    else:
        intervention = "restrict_traffic"

    # 2. Run What-If simulator request with corresponding intervention
    payload = {
        "ward_id": ward_id,
        "intervention": intervention,
        "duration_hours": 24
    }
    whatif_resp = client.post("/api/whatif", json=payload)
    assert whatif_resp.status_code == 200
    whatif_data = whatif_resp.json()
    parsed_whatif = WhatIfResponse(**whatif_data)

    # Verify matching mitigation results
    assert parsed_whatif.ward_id == ward_id
    assert parsed_whatif.intervention == intervention
    assert parsed_whatif.reduction_percentage >= 0.0
    assert parsed_whatif.with_intervention <= parsed_whatif.current_forecast

# Scenario 3: Chat session context
def test_chat_session_context(client):
    # 1. Start session by sending initial greetings / generic request
    chat_resp_1 = client.post("/api/chat", json={"message": "Hello, tell me about general AQI in Delhi", "language": "en"})
    assert chat_resp_1.status_code == 200
    data_1 = chat_resp_1.json()
    parsed_chat_1 = ChatResponse(**data_1)
    conversation_id = parsed_chat_1.conversation_id
    assert conversation_id != ""

    # 2. Ask a follow-up about Rohini using same conversation_id
    chat_resp_2 = client.post("/api/chat", json={
        "message": "Can you elaborate about Rohini air quality?",
        "language": "en",
        "conversation_id": conversation_id
    })
    assert chat_resp_2.status_code == 200
    data_2 = chat_resp_2.json()
    parsed_chat_2 = ChatResponse(**data_2)
    assert parsed_chat_2.conversation_id == conversation_id
    assert "Rohini" in parsed_chat_2.response

    # 3. Ask another follow-up about Dwarka using same conversation_id
    chat_resp_3 = client.post("/api/chat", json={
        "message": "What about Dwarka Sector 10?",
        "language": "en",
        "conversation_id": conversation_id
    })
    assert chat_resp_3.status_code == 200
    data_3 = chat_resp_3.json()
    parsed_chat_3 = ChatResponse(**data_3)
    assert parsed_chat_3.conversation_id == conversation_id
    assert "Dwarka" in parsed_chat_3.response

# Scenario 4: Vulnerable locations / Enforcement ticket correlation
def _facility(lon, lat, kind, ward_name, verified):
    props = {"name": f"{kind} test", "type": kind, "ward_id": "X", "ward_name": ward_name}
    props.update({"source": "osm", "osm_id": 1, "synthetic": False} if verified
                 else {"source": "synthetic-demo", "synthetic": True})
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props}


def test_enforcement_counts_only_verified_facilities_in_ward(client, tmp_path, monkeypatch):
    """Ticket facility counts = verified facilities inside the station's ward polygon."""
    import geopandas as gpd
    from services import places

    ticket = client.get("/api/enforce/delhi").json()["tickets"][0]
    wards = gpd.read_file(places.WARDS_PATH)
    wards["ward_id"] = wards["Ward_Name"].map(places.normalize_ward_name)
    ward = wards[wards["ward_id"] == ticket["ward_id"]].iloc[0]
    inside = ward.geometry.representative_point()
    outside = wards[wards["ward_id"] != ticket["ward_id"]].iloc[0].geometry.representative_point()

    features = [
        _facility(inside.x, inside.y, "school", ward.Ward_Name, verified=True),
        _facility(inside.x, inside.y, "school", ward.Ward_Name, verified=True),
        _facility(inside.x, inside.y, "hospital", ward.Ward_Name, verified=True),
        _facility(inside.x, inside.y, "school", ward.Ward_Name, verified=False),   # synthetic: excluded
        _facility(outside.x, outside.y, "hospital", "elsewhere", verified=True),  # other ward: excluded
    ]
    path = tmp_path / "facilities.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    monkeypatch.setattr(places, "FACILITIES_PATH", str(path))
    places.reset_cache()
    try:
        t = next(t for t in client.get("/api/enforce/delhi").json()["tickets"] if t["ward_id"] == ticket["ward_id"])
        assert t["schools_in_zone"] == 2
        assert t["hospitals_in_zone"] == 1
    finally:
        places.reset_cache()


def test_enforcement_reports_unknown_instead_of_defaults(client):
    """Bundled facilities are synthetic and some wards lack census data: report unknown, not 0 or 50,000."""
    from services import places
    data = client.get("/api/enforce/delhi").json()
    assert "unknown" in data["impact_data_note"]
    for t in data["tickets"]:
        assert t["schools_in_zone"] is None and t["hospitals_in_zone"] is None
        assert t["affected_population"] != 50000
        assert t["affected_population"] == places.ward_population(t["ward_id"])


def test_vulnerable_endpoint_flags_synthetic_records(client):
    data = client.get("/api/vulnerable/delhi").json()
    assert data["verified_locations"] == 0
    assert "synthetic" in data["data_note"]
    assert all(loc["source"] == "synthetic-demo" and not loc["verified"] for loc in data["locations"])
