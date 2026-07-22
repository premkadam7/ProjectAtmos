import os
import sys
import json
import random
import httpx

# Ensure we can import modules from backend
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set working directory to backend/ so relative imports and relative paths in other files function correctly
os.chdir(backend_dir)

from data.boundaries import get_ward_by_coords, get_wards_gdf

output_path = os.path.join("data_store", "geojson", "vulnerable_locations.geojson")

def _resolve_col(gdf, candidates):
    for c in candidates:
        if c in gdf.columns:
            return c
    return candidates[-1]

def generate_synthetic_locations():
    locations = []
    try:
        gdf = get_wards_gdf()
    except Exception as e:
        print(f"Error loading wards GDF: {e}")
        return []

    types = ["school", "hospital", "elderly_care"]
    school_names = ["Public School", "Model School", "Convent School", "Academy", "International School"]
    hospital_names = ["Super Speciality Hospital", "Apex Clinic", "General Hospital", "Health Center", "Nursing Home"]
    elderly_names = ["Senior Citizen Home", "Graceful Living Elderly Care", "Hope Assisted Living", "Nightingale Care", "Sunset Retreat"]
    
    # Bounding box constraints
    min_lat, max_lat = 28.40, 28.90
    min_lon, max_lon = 76.80, 77.40
    
    count = 0
    name_col = _resolve_col(gdf, ["Ward_Name", "WARD_NAME", "name"])
    id_col = _resolve_col(gdf, ["Ward_No", "WARD_NO", "id"])

    # Let's iterate over the wards to distribute locations evenly
    for _, row in gdf.iterrows():
        ward_name = row.get(name_col, "Unknown")
        ward_id = row.get(id_col, "Unknown")
        
        rep_pt = row["geometry"].representative_point()
        base_lon, base_lat = rep_pt.x, rep_pt.y
        
        # Generate 1 to 3 locations for this ward
        for i in range(3):
            loc_type = types[i % 3]
            if loc_type == "school":
                loc_name = f"{ward_name} {random.choice(school_names)}"
            elif loc_type == "hospital":
                loc_name = f"{ward_name} {random.choice(hospital_names)}"
            else:
                loc_name = f"{ward_name} {random.choice(elderly_names)}"
                
            # Add small random offsets (approx 100-300 meters)
            offset_lat = (random.random() - 0.5) * 0.005
            offset_lon = (random.random() - 0.5) * 0.005
            
            lat = base_lat + offset_lat
            lon = base_lon + offset_lon
            
            # Check bounding box
            if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                continue
                
            # Resolve ward to check validity
            ward_info = get_ward_by_coords(lat, lon)
            if ward_info is not None:
                locations.append({
                    "name": loc_name,
                    "type": loc_type,
                    "lat": lat,
                    "lon": lon,
                    "ward_id": ward_info["ward_id"],
                    "ward_name": ward_info["name"]
                })
                count += 1
                if count >= 60:  # Cap to avoid excessive file size
                    break
        if count >= 60:
            break
            
    # If we have fewer than 30 locations, generate generic points inside Delhi bounding box
    if len(locations) < 30:
        for i in range(100):
            if len(locations) >= 40:
                break
            lat = random.uniform(28.5, 28.8)
            lon = random.uniform(77.0, 77.3)
            ward_info = get_ward_by_coords(lat, lon)
            if ward_info:
                loc_type = types[i % 3]
                if loc_type == "school":
                    loc_name = f"Delhi District School {i}"
                elif loc_type == "hospital":
                    loc_name = f"Delhi Community Hospital {i}"
                else:
                    loc_name = f"Delhi Care Center {i}"
                locations.append({
                    "name": loc_name,
                    "type": loc_type,
                    "lat": lat,
                    "lon": lon,
                    "ward_id": ward_info["ward_id"],
                    "ward_name": ward_info["name"]
                })
                
    return locations

def fetch_from_overpass():
    url = "https://overpass-api.de/api/interpreter"
    query = """[out:json][timeout:180];
(
  node["amenity"="school"](28.40,76.80,28.90,77.40);
  way["amenity"="school"](28.40,76.80,28.90,77.40);
  
  node["amenity"="hospital"](28.40,76.80,28.90,77.40);
  way["amenity"="hospital"](28.40,76.80,28.90,77.40);
  
  node["amenity"="social_facility"]["social_facility"~"elderly|nursing|assisted_living"](28.40,76.80,28.90,77.40);
  way["amenity"="social_facility"]["social_facility"~"elderly|nursing|assisted_living"](28.40,76.80,28.90,77.40);
);
out center;"""

    try:
        print("Sending request to Overpass API...")
        response = httpx.post(url, data={"data": query}, timeout=15.0)
        if response.status_code != 200:
            print(f"Overpass API returned status code {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        print(f"Failed to fetch from Overpass API (will use fallback): {e}")
        return None

def main():
    data = fetch_from_overpass()
    
    locations = []
    if data and "elements" in data:
        elements = data["elements"]
        print(f"Fetched {len(elements)} elements from Overpass.")
        
        for elem in elements:
            tags = elem.get("tags", {})
            amenity = tags.get("amenity")
            
            # Determine type
            if amenity == "school":
                loc_type = "school"
            elif amenity == "hospital":
                loc_type = "hospital"
            elif amenity == "social_facility":
                loc_type = "elderly_care"
            else:
                # Fallback check on social_facility tag
                sf_tag = tags.get("social_facility", "")
                if any(k in sf_tag for k in ["elderly", "nursing", "assisted_living"]):
                    loc_type = "elderly_care"
                else:
                    continue
            
            # Determine coordinates
            if elem.get("type") == "node":
                lat = elem.get("lat")
                lon = elem.get("lon")
            else:
                center = elem.get("center", {})
                lat = center.get("lat")
                lon = center.get("lon")
                
            if lat is None or lon is None:
                continue
                
            # Resolve ward
            try:
                ward_info = get_ward_by_coords(lat, lon)
            except Exception as e:
                print(f"Error resolving ward for coordinates ({lat}, {lon}): {e}")
                ward_info = None
                
            if ward_info is None:
                continue
                
            ward_id = ward_info.get("ward_id")
            ward_name = ward_info.get("name")
            
            # Get name
            name = tags.get("name")
            if not name:
                name = f"{loc_type.capitalize()} near {ward_name}"
                
            locations.append({
                "name": name,
                "type": loc_type,
                "lat": lat,
                "lon": lon,
                "ward_id": ward_id,
                "ward_name": ward_name
            })
            
    if not locations:
        print("No locations fetched or request failed/returned empty. Using high-quality synthetic fallback...")
        locations = generate_synthetic_locations()
        print(f"Generated {len(locations)} synthetic locations.")
        
    # Convert locations list to GeoJSON FeatureCollection
    features = []
    for loc in locations:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [loc["lon"], loc["lat"]]
            },
            "properties": {
                "name": loc["name"],
                "type": loc["type"],
                "ward_id": loc["ward_id"],
                "ward_name": loc["ward_name"]
            }
        }
        features.append(feature)
        
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Save cache file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)
    print(f"Successfully saved {len(locations)} locations to {output_path}")

if __name__ == "__main__":
    main()
