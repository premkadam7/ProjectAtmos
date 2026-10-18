import os
import json
import ee
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from data.ndvi_table import NDVI_PATH, NdviSchemaError, write_ndvi_table

def authenticate_and_initialize():
    try:
        ee.Initialize(project=os.environ.get("GOOGLE_CLOUD_PROJECT", "atmos-aqi"))
    except Exception as e:
        print("Earth Engine is not initialized.")
        print("Please run `venv/bin/earthengine authenticate` in your terminal.")
        print("And set your project using `venv/bin/earthengine set_project YOUR_PROJECT_ID`")
        sys.exit(1)

def get_ndvi_for_wards():
    cache_dir = os.path.join("data_store", "cache")
    geojson_path = os.path.join("data_store", "geojson", "delhi_wards.geojson")
    output_path = NDVI_PATH

    if not os.path.exists(geojson_path):
        print(f"GeoJSON not found: {geojson_path}")
        sys.exit(1)

    print("Loading GeoJSON...")
    with open(geojson_path, "r") as f:
        geojson_data = json.load(f)

    # Earth Engine image collection (Sentinel-2 SR)
    # We take a median composite of 2023 to represent the baseline green cover
    print("Querying Sentinel-2 Imagery...")
    s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate('2023-01-01', '2023-12-31') \
        .filterBounds(ee.Geometry.Point([77.2090, 28.6139])) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .median()

    # Calculate NDVI: (NIR - RED) / (NIR + RED) -> (B8 - B4) / (B8 + B4)
    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('NDVI')

    results = []
    
    print("Computing Zonal Statistics for wards...")
    features = geojson_data.get("features", [])
    total = len(features)
    
    for i, feature in enumerate(features):
        props = feature.get("properties", {})
        # Keyed by Ward_Name, the column preprocess.py joins on
        ward_name = props.get("Ward_Name", props.get("WARD_NAME", "Unknown"))
        
        geom = feature.get("geometry")
        if not geom:
            continue
            
        try:
            ee_geom = ee.Geometry(geom)
            
            # Get mean NDVI for this polygon
            stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee_geom,
                scale=10,
                maxPixels=1e9
            ).getInfo()
            
            results.append({"Ward_Name": ward_name, "ndvi_mean": stats.get('NDVI')})
            
            if (i+1) % 10 == 0:
                print(f"Processed {i+1}/{total} wards...")
                
        except Exception as e:
            # Leave the value empty: 0.0 would claim the ward has no vegetation
            print(f"Failed to process ward {ward_name}: {e}")
            results.append({"Ward_Name": ward_name, "ndvi_mean": None})

    expected = [f.get("properties", {}).get("Ward_Name") for f in features]
    try:
        write_ndvi_table(results, expected, output_path)
    except NdviSchemaError as e:
        print(f"Not saving NDVI data: {e}")
        sys.exit(1)
    print(f"Saved NDVI data to {output_path}")

if __name__ == "__main__":
    authenticate_and_initialize()
    get_ndvi_for_wards()
