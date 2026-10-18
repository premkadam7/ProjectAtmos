"""Ward-level reference data: population and vulnerable facilities.

Stations and municipal wards are different entities: each monitoring
station is assigned the canonical id of the ward polygon it sits in
(``ward_id`` in the feature data, a normalised ward name). Population and
facility counts are joined on that id, never on a station's display name.

Facilities carry provenance: records fetched from OpenStreetMap have
``source: "osm"``; generated placeholder records have ``synthetic: true``.
Only verified (non-synthetic) facilities are counted. When no verified
data exists, counts are ``None`` ("unknown"), not zero.
"""
import json
import os
import re
import threading

import geopandas as gpd
import pandas as pd

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
POPULATION_PATH = os.path.join(BACKEND_DIR, "data_store", "cache", "delhi_wards_population.csv")
WARDS_PATH = os.path.join(BACKEND_DIR, "data_store", "geojson", "delhi_wards.geojson")
FACILITIES_PATH = os.path.join(BACKEND_DIR, "data_store", "geojson", "vulnerable_locations.geojson")

_lock = threading.Lock()
_cache = {}


def normalize_ward_name(name) -> str:
    """Canonical ward id, matching data/preprocess.py."""
    return re.sub(r"\s+", "_", str(name).strip()).lower()


def is_verified(props: dict) -> bool:
    return not props.get("synthetic", False) and props.get("source") == "osm"


def load_facilities(path: str = None) -> list:
    with open(path or FACILITIES_PATH, encoding="utf-8") as f:
        return json.load(f).get("features", [])


def _build():
    pop = pd.read_csv(POPULATION_PATH)
    population = {
        normalize_ward_name(n): int(p)
        for n, p in zip(pop["ward_name"], pop["population"]) if not pd.isna(p)
    }

    wards = gpd.read_file(WARDS_PATH)[["Ward_Name", "geometry"]]
    wards["ward_id"] = wards["Ward_Name"].map(normalize_ward_name)

    try:
        features = load_facilities()
    except (OSError, ValueError):
        features = []
    verified = [f for f in features if is_verified(f.get("properties", {}))]

    counts = {}
    if verified:
        pts = gpd.GeoDataFrame(
            {"type": [f["properties"].get("type") for f in verified]},
            geometry=gpd.points_from_xy(
                [f["geometry"]["coordinates"][0] for f in verified],
                [f["geometry"]["coordinates"][1] for f in verified],
            ),
            crs=wards.crs,
        )
        joined = gpd.sjoin(pts, wards, predicate="within", how="inner")
        for (ward_id, kind), n in joined.groupby(["ward_id", "type"]).size().items():
            counts.setdefault(ward_id, {})[kind] = int(n)

    return {
        "population": population,
        "facility_counts": counts,
        "facilities_verified": bool(verified),
        "facility_records": len(features),
        "verified_records": len(verified),
    }


def reference_data():
    with _lock:
        if not _cache:
            _cache.update(_build())
        return dict(_cache)


def reset_cache():
    with _lock:
        _cache.clear()


def ward_population(ward_id: str):
    """Population of a ward, or None when the census table has no figure."""
    return reference_data()["population"].get(ward_id)


def ward_facility_count(ward_id: str, kind: str):
    """Verified facilities of a kind inside a ward polygon, or None if unknown."""
    data = reference_data()
    if not data["facilities_verified"]:
        return None
    return data["facility_counts"].get(ward_id, {}).get(kind, 0)
