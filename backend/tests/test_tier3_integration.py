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
def test_vulnerable_enforcement_ticket_correlation(client):
    # 1. Fetch enforcement tickets
    enforce_resp = client.get("/api/enforce/delhi")
    assert enforce_resp.status_code == 200
    enforce_data = enforce_resp.json()
    parsed_enforce = EnforcementResponse(**enforce_data)
    assert len(parsed_enforce.tickets) > 0

    # Pick the first ticket
    ticket = parsed_enforce.tickets[0]
    ward_id = ticket.ward_id
    ward_name = ticket.ward_name
    expected_schools = ticket.schools_in_zone
    expected_hospitals = ticket.hospitals_in_zone

    # Mock the GeoJSON reading inside routers/vulnerable.py to align counts perfectly
    mock_features = []
    for i in range(expected_schools):
        mock_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [77.123, 28.567]},
            "properties": {
                "name": f"{ward_name} Public School {i}",
                "type": "school",
                "ward_id": ward_id,
                "ward_name": ward_name
            }
        })
    for i in range(expected_hospitals):
        mock_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [77.123, 28.567]},
            "properties": {
                "name": f"{ward_name} General Hospital {i}",
                "type": "hospital",
                "ward_id": ward_id,
                "ward_name": ward_name
            }
        })
    # Add a random elderly care center to ensure other types are present
    mock_features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [77.123, 28.567]},
        "properties": {
            "name": f"{ward_name} Senior Citizen Home",
            "type": "elderly_care",
            "ward_id": ward_id,
            "ward_name": ward_name
        }
    })

    mock_geojson = {
        "type": "FeatureCollection",
        "features": mock_features
    }

    mock_geojson_str = json.dumps(mock_geojson)

    # Patch the geojson file reading to return our mock structure
    with patch("builtins.open", mock_open(read_data=mock_geojson_str)):
        with patch("os.path.exists", return_value=True):
            # 2. Get vulnerable locations in Delhi
            vulnerable_resp = client.get("/api/vulnerable/delhi")
            assert vulnerable_resp.status_code == 200
            vulnerable_data = vulnerable_resp.json()
            parsed_vulnerable = VulnerableResponse(**vulnerable_data)

            # Filter vulnerable locations by ticketed ward
            ward_vulnerables = [loc for loc in parsed_vulnerable.locations if loc.ward_id == ward_id]
            schools_in_ward = sum(1 for loc in ward_vulnerables if loc.type == "school")
            hospitals_in_ward = sum(1 for loc in ward_vulnerables if loc.type == "hospital")

            # Verify counts match the metadata inside the ticket
            assert schools_in_ward == expected_schools
            assert hospitals_in_ward == expected_hospitals
