import json
import os
import geopandas as gpd
from shapely.geometry import Point

CACHE_DIR = os.path.join("data_store", "geojson")
GEOJSON_PATH = os.path.join(CACHE_DIR, "delhi_wards.geojson")

_gdf = None

def get_wards_gdf():
    global _gdf
    if _gdf is None:
        if not os.path.exists(GEOJSON_PATH):
            raise FileNotFoundError(f"GeoJSON not found at {GEOJSON_PATH}")
        _gdf = gpd.read_file(GEOJSON_PATH)
    return _gdf

def _resolve_col(gdf, candidates):
    for c in candidates:
        if c in gdf.columns:
            return c
    return candidates[-1]

def list_all_wards():
    gdf = get_wards_gdf()
    name_col = _resolve_col(gdf, ["Ward_Name", "WARD_NAME", "name"])
    id_col = _resolve_col(gdf, ["Ward_No", "WARD_NO", "id"])

    return [
        {"ward_id": row.get(id_col, row.get(name_col, "Unknown")),
         "name": row.get(name_col, "Unknown")}
        for _, row in gdf.iterrows()
    ]

def get_ward_by_coords(lat: float, lon: float):
    gdf = get_wards_gdf()
    point = Point(lon, lat)
    name_col = _resolve_col(gdf, ["Ward_Name", "WARD_NAME", "name"])
    id_col = _resolve_col(gdf, ["Ward_No", "WARD_NO", "id"])

    for _, row in gdf.iterrows():
        if row["geometry"].contains(point):
            return {
                "ward_id": row.get(id_col, row.get(name_col, "Unknown")),
                "name": row.get(name_col, "Unknown")
            }
    return None

def get_ward_geojson(ward_name: str):
    gdf = get_wards_gdf()
    name_col = _resolve_col(gdf, ["Ward_Name", "WARD_NAME", "name"])

    match = gdf[gdf[name_col].str.lower() == ward_name.lower()]
    if match.empty:
        return None
    return json.loads(match.to_json())
