import os
import json
import pytest
from data.fetch_vulnerable import generate_synthetic_locations, output_path

def test_generate_synthetic_locations():
    """
    Test that the synthetic locations generator produces valid locations
    with the required structures, coordinates, and types.
    """
    locations = generate_synthetic_locations()
    assert len(locations) >= 30
    for loc in locations:
        assert "name" in loc
        assert "type" in loc
        assert "lat" in loc
        assert "lon" in loc
        assert "ward_id" in loc
        assert "ward_name" in loc
        assert loc["type"] in ("school", "hospital", "elderly_care")
        assert 28.40 <= loc["lat"] <= 28.90
        assert 76.80 <= loc["lon"] <= 77.40

def test_geojson_file_creation():
    """
    Test that the generated GeoJSON file is a valid FeatureCollection
    containing point coordinates and the required properties.
    """
    assert os.path.exists(output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 30
    for feature in data["features"]:
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Point"
        coords = feature["geometry"]["coordinates"]
        assert len(coords) == 2
        props = feature["properties"]
        assert "name" in props
        assert "type" in props
        assert "ward_id" in props
        assert "ward_name" in props
