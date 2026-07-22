import os
import json
import pytest
from fastapi.testclient import TestClient
from models.schemas import VulnerableResponse

GEOJSON_PATH = os.path.join("data_store", "geojson", "vulnerable_locations.geojson")

def test_vulnerable_case_insensitivity(client):
    """
    Test that the vulnerable locations endpoint is case-insensitive for Delhi
    and correctly handles other cities.
    """
    for city_variant in ["delhi", "Delhi", "DELHI"]:
        response = client.get(f"/api/vulnerable/{city_variant}")
        assert response.status_code == 200
        data = response.json()
        parsed = VulnerableResponse(**data)
        # The returned response should match the input city exactly (or lowercase)
        assert parsed.city == city_variant
        assert parsed.total_locations > 0
        assert len(parsed.locations) == parsed.total_locations

    for other_city in ["mumbai", "MUMBAI", "newyork"]:
        response = client.get(f"/api/vulnerable/{other_city}")
        assert response.status_code == 200
        data = response.json()
        parsed = VulnerableResponse(**data)
        assert parsed.city == other_city
        assert parsed.total_locations == 0
        assert len(parsed.locations) == 0

def test_vulnerable_geojson_deletion_resilience(client):
    """
    Test that if the GeoJSON cache file is deleted, the router handles it
    by invoking the generator and successfully recreating the GeoJSON
    without returning an error.
    """
    # Backup original geojson if it exists
    original_geojson_content = None
    if os.path.exists(GEOJSON_PATH):
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            original_geojson_content = f.read()
        os.remove(GEOJSON_PATH)

    try:
        # Confirm that the file is gone
        assert not os.path.exists(GEOJSON_PATH)

        # Call the API endpoint
        response = client.get("/api/vulnerable/delhi")
        assert response.status_code == 200
        data = response.json()
        parsed = VulnerableResponse(**data)
        assert parsed.city == "delhi"
        assert parsed.total_locations >= 30

        # Verify that the file was recreated on disk
        assert os.path.exists(GEOJSON_PATH)
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            recreated_data = json.load(f)
        assert recreated_data["type"] == "FeatureCollection"
        assert len(recreated_data["features"]) >= 30

    finally:
        # Restore the original geojson content
        if original_geojson_content is not None:
            os.makedirs(os.path.dirname(GEOJSON_PATH), exist_ok=True)
            with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
                f.write(original_geojson_content)

def test_vulnerable_geojson_corrupted_resilience(client):
    """
    Test that if the GeoJSON cache file is corrupted (invalid JSON),
    the router raises a 500 error.
    """
    # Backup original geojson if it exists
    original_geojson_content = None
    if os.path.exists(GEOJSON_PATH):
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            original_geojson_content = f.read()

    try:
        # Write corrupted JSON to the file
        os.makedirs(os.path.dirname(GEOJSON_PATH), exist_ok=True)
        with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
            f.write("{invalid_json: true")

        # Call the API endpoint
        response = client.get("/api/vulnerable/delhi")
        # Since it's corrupted, we expect HTTP 500 Internal Server Error
        assert response.status_code == 500
        assert "Failed to read vulnerable locations data" in response.json()["detail"]

    finally:
        # Restore the original geojson content
        if original_geojson_content is not None:
            os.makedirs(os.path.dirname(GEOJSON_PATH), exist_ok=True)
            with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
                f.write(original_geojson_content)

