import os
import json
import pytest
from fastapi.testclient import TestClient
from models.schemas import VulnerableResponse

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
        assert response.status_code == 404

@pytest.fixture
def facility_file(tmp_path, monkeypatch):
    """Point the facility endpoint at a temporary copy, never the tracked file."""
    import routers.vulnerable as vulnerable
    from services import places

    path = tmp_path / "vulnerable_locations.geojson"
    path.write_bytes(open(vulnerable.GEOJSON_PATH, "rb").read())
    monkeypatch.setattr(vulnerable, "GEOJSON_PATH", str(path))
    monkeypatch.setattr(places, "FACILITIES_PATH", str(path))
    places.reset_cache()
    yield path
    places.reset_cache()


def test_vulnerable_geojson_deletion_resilience(client, facility_file):
    """A missing facility file is regenerated (as flagged synthetic data) without an error."""
    facility_file.unlink()

    response = client.get("/api/vulnerable/delhi")
    assert response.status_code == 200
    parsed = VulnerableResponse(**response.json())
    assert parsed.city == "delhi"
    assert parsed.total_locations >= 30
    # External calls are mocked, so the generator falls back to placeholders
    assert parsed.verified_locations == 0

    recreated = json.loads(facility_file.read_text(encoding="utf-8"))
    assert recreated["type"] == "FeatureCollection"
    assert len(recreated["features"]) >= 30
    assert all(f["properties"]["synthetic"] for f in recreated["features"])


def test_vulnerable_geojson_corrupted_resilience(client, facility_file):
    """A corrupted facility file is a clear 500, not a crash."""
    facility_file.write_text("{invalid_json: true", encoding="utf-8")

    response = client.get("/api/vulnerable/delhi")
    assert response.status_code == 500
    assert "Failed to read vulnerable locations data" in response.json()["detail"]
