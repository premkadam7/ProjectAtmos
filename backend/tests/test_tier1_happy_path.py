import pytest
from fastapi.testclient import TestClient
from models.schemas import (
    VulnerableResponse,
    WhatIfResponse,
    ChatResponse,
    CityForecastResponse,
    WardForecastDetailResponse,
    BlameResponse,
    EnforcementResponse
)

# ── FEATURE 1: Chat Assistant Endpoints ──

def test_chat_default_english(client):
    response = client.post("/api/chat", json={"message": "What is Delhi's average AQI?", "language": "en"})
    assert response.status_code == 200
    data = response.json()
    parsed = ChatResponse(**data)
    assert parsed.language == "en"
    assert parsed.conversation_id is not None
    assert "Delhi's average AQI is 215" in parsed.response
    assert "Forecast Data" in parsed.sources

def test_chat_rohini_query(client):
    response = client.post("/api/chat", json={"message": "Tell me about Rohini", "language": "en"})
    assert response.status_code == 200
    data = response.json()
    parsed = ChatResponse(**data)
    assert "Rohini" in parsed.response
    assert "245" in parsed.response

def test_chat_dwarka_query(client):
    response = client.post("/api/chat", json={"message": "How is Dwarka's air quality?", "language": "en"})
    assert response.status_code == 200
    data = response.json()
    parsed = ChatResponse(**data)
    assert "Dwarka" in parsed.response
    assert "185" in parsed.response

def test_chat_jogging_query(client):
    response = client.post("/api/chat", json={"message": "Can I go jogging tomorrow?", "language": "en"})
    assert response.status_code == 200
    data = response.json()
    parsed = ChatResponse(**data)
    assert "jogging" in parsed.response or "exercise" in parsed.response or "Vasant Kunj" in parsed.response

def test_chat_hindi_default(client):
    response = client.post("/api/chat", json={"message": "दिल्ली का AQI क्या है?", "language": "hi"})
    assert response.status_code == 200
    data = response.json()
    parsed = ChatResponse(**data)
    assert parsed.language == "hi"
    assert "दिल्ली का औसत AQI 215" in parsed.response

def test_chat_hindi_rohini(client):
    response = client.post("/api/chat", json={"message": "रोहिणी सेक्टर 7 की स्थिति क्या है?", "language": "hi"})
    assert response.status_code == 200
    data = response.json()
    parsed = ChatResponse(**data)
    assert parsed.language == "hi"
    assert "रोहिणी सेक्टर 7" in parsed.response or "245" in parsed.response


# ── FEATURE 2: Vulnerable Locations Endpoints ──

def test_vulnerable_delhi_success(client):
    response = client.get("/api/vulnerable/delhi")
    assert response.status_code == 200
    data = response.json()
    parsed = VulnerableResponse(**data)
    assert parsed.city == "delhi"
    assert parsed.total_locations > 0
    assert len(parsed.locations) == parsed.total_locations

def test_vulnerable_other_city(client):
    response = client.get("/api/vulnerable/mumbai")
    assert response.status_code == 200
    data = response.json()
    parsed = VulnerableResponse(**data)
    assert parsed.city == "mumbai"

def test_vulnerable_location_types(client):
    response = client.get("/api/vulnerable/delhi")
    data = response.json()
    parsed = VulnerableResponse(**data)
    types_found = {loc.type for loc in parsed.locations}
    assert any(t in types_found for t in ("hospital", "school", "elderly_care"))

def test_vulnerable_coordinate_bounds(client):
    response = client.get("/api/vulnerable/delhi")
    data = response.json()
    parsed = VulnerableResponse(**data)
    for loc in parsed.locations:
        assert 28.0 <= loc.lat <= 29.5
        assert 76.5 <= loc.lon <= 77.8

def test_vulnerable_fields_non_empty(client):
    response = client.get("/api/vulnerable/delhi")
    data = response.json()
    parsed = VulnerableResponse(**data)
    for loc in parsed.locations:
        assert loc.name != ""
        assert loc.ward_id != ""
        assert loc.ward_name != ""


# ── FEATURE 3: What-If Simulator Endpoints ──

def test_whatif_traffic_intervention(client):
    overview_resp = client.get("/api/forecast/delhi")
    assert overview_resp.status_code == 200
    wards = overview_resp.json().get("wards", [])
    ward_id = wards[0]["ward_id"] if wards else "rohini_sector_7"

    payload = {
        "ward_id": ward_id,
        "intervention": "restrict_traffic",
        "duration_hours": 24
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 200
    data = response.json()
    parsed = WhatIfResponse(**data)
    assert parsed.ward_id == ward_id
    assert parsed.intervention == "restrict_traffic"
    assert parsed.reduction_percentage >= 0.0
    assert parsed.reduction >= 0.0

def test_whatif_construction_intervention(client):
    overview_resp = client.get("/api/forecast/delhi")
    wards = overview_resp.json().get("wards", [])
    ward_id = wards[0]["ward_id"] if wards else "rohini_sector_7"

    payload = {
        "ward_id": ward_id,
        "intervention": "pause_construction",
        "duration_hours": 48
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 200
    data = response.json()
    parsed = WhatIfResponse(**data)
    assert parsed.intervention == "pause_construction"
    assert parsed.reduction_percentage >= 0.0

def test_whatif_factory_intervention(client):
    overview_resp = client.get("/api/forecast/delhi")
    wards = overview_resp.json().get("wards", [])
    ward_id = wards[0]["ward_id"] if wards else "rohini_sector_7"

    payload = {
        "ward_id": ward_id,
        "intervention": "pause factory industrial emissions",
        "duration_hours": 72
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 200
    data = response.json()
    parsed = WhatIfResponse(**data)
    assert parsed.reduction_percentage >= 0.0

def test_whatif_other_intervention(client):
    payload = {
        "ward_id": "rohini_sector_7",
        "intervention": "some random intervention",
        "duration_hours": 12
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 200
    data = response.json()
    parsed = WhatIfResponse(**data)
    assert parsed.reduction_percentage >= 0.0

def test_whatif_invalid_ward_fallback(client):
    payload = {
        "ward_id": "non_existent_ward_123",
        "intervention": "pause_construction",
        "duration_hours": 48
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 200
    data = response.json()
    parsed = WhatIfResponse(**data)
    assert parsed.ward_id == "non_existent_ward_123"
    assert parsed.current_forecast > 0


# ── FEATURE 4: Demo Pre-computation Endpoints ──

def test_precompute_city_overview(client):
    response = client.get("/api/forecast/delhi")
    assert response.status_code == 200
    data = response.json()
    parsed = CityForecastResponse(**data)
    assert parsed.city == "delhi"
    assert parsed.total_wards > 0
    assert len(parsed.wards) == parsed.total_wards

def test_precompute_ward_forecast(client):
    overview_resp = client.get("/api/forecast/delhi")
    wards = overview_resp.json().get("wards", [])
    assert len(wards) > 0
    ward_id = wards[0]["ward_id"]

    response = client.get(f"/api/forecast/delhi/{ward_id}")
    assert response.status_code == 200
    data = response.json()
    parsed = WardForecastDetailResponse(**data)
    assert parsed.ward_id == ward_id
    assert len(parsed.hourly) == 72
    for h in parsed.hourly:
        assert h.aqi > 0
        assert h.aqi_low <= h.aqi <= h.aqi_high

def test_precompute_blame_score(client):
    overview_resp = client.get("/api/forecast/delhi")
    wards = overview_resp.json().get("wards", [])
    assert len(wards) > 0
    ward_id = wards[0]["ward_id"]

    response = client.get(f"/api/blame/delhi/{ward_id}")
    assert response.status_code == 200
    data = response.json()
    parsed = BlameResponse(**data)
    assert parsed.ward_id == ward_id
    assert len(parsed.factors) > 0
    total_pct = sum(f.percentage for f in parsed.factors)
    assert 99.0 <= total_pct <= 101.0

def test_precompute_enforcement_tickets(client):
    response = client.get("/api/enforce/delhi")
    assert response.status_code == 200
    data = response.json()
    parsed = EnforcementResponse(**data)
    assert parsed.city == "delhi"
    assert len(parsed.tickets) == parsed.total_tickets
    for ticket in parsed.tickets:
        assert ticket.urgency in ("HIGH", "MEDIUM", "LOW")
        assert ticket.current_aqi >= 100

def test_precompute_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data
