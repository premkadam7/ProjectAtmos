import pytest
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from models.schemas import (
    ChatResponse,
    VulnerableResponse,
    WhatIfResponse,
    CityForecastResponse,
    WardForecastDetailResponse,
    BlameResponse
)

# --- Chat Assistant Boundaries & Corner Cases ---

def test_chat_empty_message(client):
    # Empty message should either succeed with default response or be handled gracefully
    response = client.post("/api/chat", json={"message": "", "language": "en"})
    assert response.status_code == 200
    data = response.json()
    parsed = ChatResponse(**data)
    assert parsed.language == "en"
    assert parsed.conversation_id is not None
    assert len(parsed.response) > 0

def test_chat_fallback_language(client):
    # Unsupported language should fall back to English
    response = client.post("/api/chat", json={"message": "What is the AQI?", "language": "fr"})
    assert response.status_code == 200
    data = response.json()
    parsed = ChatResponse(**data)
    # The API returns the requested language but uses English pool
    assert parsed.language == "fr"
    assert "Delhi's average AQI is 215" in parsed.response

def test_chat_invalid_json(client):
    # Malformed JSON payload should result in 422 Unprocessable Entity
    response = client.post("/api/chat", content="{'invalid_json': }", headers={"Content-Type": "application/json"})
    assert response.status_code == 422

def test_chat_extremely_long_message(client):
    # Extremely long message should be accepted and processed
    long_msg = "A" * 5000
    response = client.post("/api/chat", json={"message": long_msg, "language": "en"})
    assert response.status_code == 200
    data = response.json()
    assert ChatResponse(**data).conversation_id is not None

def test_chat_missing_required_fields(client):
    # Missing required message field should cause a 422 validation error
    response = client.post("/api/chat", json={"language": "en"})
    assert response.status_code == 422


# --- Vulnerable Locations Boundaries & Corner Cases ---

def test_vulnerable_invalid_city(client):
    # Querying a city other than Delhi should return an empty response list (200 OK)
    response = client.get("/api/vulnerable/mumbai")
    assert response.status_code == 200
    data = response.json()
    parsed = VulnerableResponse(**data)
    assert parsed.city == "mumbai"
    assert parsed.total_locations == 0
    assert len(parsed.locations) == 0

def test_vulnerable_empty_city_404(client):
    # Empty city path parameter should return a 404 error
    response = client.get("/api/vulnerable/")
    assert response.status_code == 404

def test_vulnerable_case_insensitivity(client):
    # City name should be case-insensitive
    response = client.get("/api/vulnerable/DeLhI")
    assert response.status_code == 200
    data = response.json()
    parsed = VulnerableResponse(**data)
    assert parsed.city == "DeLhI"
    assert parsed.total_locations > 0

def test_vulnerable_special_chars_city(client):
    # Special characters in city should not cause server crash and return empty list
    response = client.get("/api/vulnerable/delhi!@#")
    assert response.status_code == 200
    data = response.json()
    assert data["total_locations"] == 0

def test_vulnerable_very_long_city_name(client):
    # Extremely long city name should return empty locations list
    long_city = "delhi" * 100
    response = client.get(f"/api/vulnerable/{long_city}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_locations"] == 0


# --- What-If Simulator Boundaries & Corner Cases ---

def test_whatif_out_of_bounds_hours_positive(client):
    # Check that high duration hours are accepted and handled
    payload = {
        "ward_id": "anand_vihar",
        "intervention": "restrict_traffic",
        "duration_hours": 100
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 200
    data = response.json()
    parsed = WhatIfResponse(**data)
    assert parsed.duration_hours == 100
    assert parsed.reduction > 0

def test_whatif_out_of_bounds_hours_negative(client):
    payload = {
        "ward_id": "anand_vihar",
        "intervention": "restrict_traffic",
        "duration_hours": -10
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 422

def test_whatif_missing_ward(client):
    # Invalid or non-existent ward should fallback to the first ward in latest features
    payload = {
        "ward_id": "non_existent_ward_xyz",
        "intervention": "pause_construction",
        "duration_hours": 48
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 200
    data = response.json()
    parsed = WhatIfResponse(**data)
    assert parsed.ward_id == "non_existent_ward_xyz"
    assert parsed.current_forecast > 0

def test_whatif_invalid_json(client):
    # Sending malformed JSON to whatif endpoint should return 422
    response = client.post("/api/whatif", content="{'ward_id': }", headers={"Content-Type": "application/json"})
    assert response.status_code == 422

def test_whatif_empty_intervention(client):
    # Empty intervention should be handled and return low default reduction (5%)
    payload = {
        "ward_id": "anand_vihar",
        "intervention": "",
        "duration_hours": 24
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 200
    data = response.json()
    parsed = WhatIfResponse(**data)
    assert parsed.reduction_percentage >= 0.0


# --- Forecast/Pre-computation Boundaries & Corner Cases ---

def test_forecast_hours_negative(client):
    # Hours < 1 should return 422 validation error
    response = client.get("/api/forecast/delhi/anand_vihar?hours=-1")
    assert response.status_code == 422

def test_forecast_hours_too_high(client):
    # Hours > 72 should return 422 validation error
    response = client.get("/api/forecast/delhi/anand_vihar?hours=73")
    assert response.status_code == 422

def test_forecast_hours_non_numeric(client):
    # Non-numeric hours should return 422 validation error
    response = client.get("/api/forecast/delhi/anand_vihar?hours=invalid")
    assert response.status_code == 422

def test_forecast_missing_city_404(client):
    # Missing city parameter should result in a 404 Not Found error
    response = client.get("/api/forecast/")
    assert response.status_code == 404

def test_blame_missing_ward_404(client):
    # Mocking get_ward_blame to return None triggers a 404 exception in the blame route
    with patch("routers.blame.get_ward_blame", return_value=None):
        response = client.get("/api/blame/delhi/invalid_ward_123")
        assert response.status_code == 404
        assert "No data for ward" in response.json()["detail"]

def test_forecast_hours_boundaries(client):
    # Test valid boundaries: hours=1 and hours=72
    response_1 = client.get("/api/forecast/delhi/anand_vihar?hours=1")
    assert response_1.status_code == 200
    assert len(response_1.json()["hourly"]) == 1

    response_72 = client.get("/api/forecast/delhi/anand_vihar?hours=72")
    assert response_72.status_code == 200
    assert len(response_72.json()["hourly"]) == 72
