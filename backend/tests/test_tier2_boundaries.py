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
    # The API returns the requested language but answers in English
    assert parsed.language == "fr"
    assert "Delhi's average AQI is" in parsed.response

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
    # Querying a city other than Delhi is rejected consistently with other routes
    response = client.get("/api/vulnerable/mumbai")
    assert response.status_code == 404

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
    assert response.status_code == 404

def test_vulnerable_very_long_city_name(client):
    # Extremely long city name should return empty locations list
    long_city = "delhi" * 100
    response = client.get(f"/api/vulnerable/{long_city}")
    assert response.status_code == 404


# --- What-If Simulator Boundaries & Corner Cases ---

def test_whatif_out_of_bounds_hours_positive(client):
    # Check that high duration hours are accepted and handled
    payload = {
        "ward_id": "i.p_extention",
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
        "ward_id": "i.p_extention",
        "intervention": "restrict_traffic",
        "duration_hours": -10
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 422

def test_whatif_missing_ward(client):
    # A non-existent ward is a 404, never another station's numbers
    payload = {
        "ward_id": "non_existent_ward_xyz",
        "intervention": "pause_construction",
        "duration_hours": 48
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 404

def test_whatif_invalid_json(client):
    # Sending malformed JSON to whatif endpoint should return 422
    response = client.post("/api/whatif", content="{'ward_id': }", headers={"Content-Type": "application/json"})
    assert response.status_code == 422

def test_whatif_empty_intervention(client):
    # An empty intervention has no counterfactual and is rejected
    payload = {
        "ward_id": "i.p_extention",
        "intervention": "",
        "duration_hours": 24
    }
    response = client.post("/api/whatif", json=payload)
    assert response.status_code == 422

# --- Forecast/Pre-computation Boundaries & Corner Cases ---

def test_forecast_hours_negative(client):
    # Hours < 1 should return 422 validation error
    response = client.get("/api/forecast/delhi/i.p_extention?hours=-1")
    assert response.status_code == 422

def test_forecast_hours_too_high(client):
    # Hours > 72 should return 422 validation error
    response = client.get("/api/forecast/delhi/i.p_extention?hours=73")
    assert response.status_code == 422

def test_forecast_hours_non_numeric(client):
    # Non-numeric hours should return 422 validation error
    response = client.get("/api/forecast/delhi/i.p_extention?hours=invalid")
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
    response_1 = client.get("/api/forecast/delhi/i.p_extention?hours=1")
    assert response_1.status_code == 200
    assert len(response_1.json()["hourly"]) == 1

    response_72 = client.get("/api/forecast/delhi/i.p_extention?hours=72")
    assert response_72.status_code == 200
    assert len(response_72.json()["hourly"]) == 72


# --- Identity and city validation (F11) ---

@pytest.mark.parametrize("path", [
    "/api/forecast/delhi/no_such_ward",
    "/api/blame/delhi/no_such_ward",
    "/api/history/delhi?ward_id=no_such_ward",
])
def test_unknown_ward_is_404_everywhere(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert "no_such_ward" in response.json()["detail"]


@pytest.mark.parametrize("path", [
    "/api/forecast/mumbai",
    "/api/forecast/mumbai/timeline",
    "/api/forecast/mumbai/i.p_extention",
    "/api/blame/mumbai/i.p_extention",
    "/api/enforce/mumbai",
    "/api/history/mumbai",
    "/api/vulnerable/mumbai",
])
def test_unsupported_city_is_404_everywhere(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert "Unsupported city" in response.json()["detail"]


def test_city_is_case_insensitive(client):
    assert client.get("/api/forecast/Delhi").status_code == 200
