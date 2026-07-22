"""
Download Delhi ward boundary GeoJSON from DataMeet GitHub.
"""
import requests
import json
import os

OUTPUT_DIR = os.path.join("data_store", "geojson")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "delhi_wards.geojson")

def download_geojson():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    url = "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Delhi/Delhi_Wards.geojson"
    print(f"Downloading GeoJSON from {url}...")
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        geojson = resp.json()
        feature_count = len(geojson.get("features", []))
        print(f"Downloaded {feature_count} features from DataMeet")
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False)
        print(f"Saved to {OUTPUT_FILE}")
        return True
    except Exception as e:
        print(f"Failed to download from DataMeet: {e}")
        return False

if __name__ == "__main__":
    download_geojson()
