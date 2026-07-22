import pandas as pd
import requests
import os
import time

DELHI_STATIONS = {
    "Punjabi Bagh": {"lat": 28.6741, "lon": 77.1310},
    "Shadipur": {"lat": 28.6515, "lon": 77.1588},
}

_NAQI_BREAKPOINTS = [
    (0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200),
    (91, 120, 201, 300), (121, 250, 301, 400), (250, 500, 401, 500),
]

def calculate_aqi_from_pm25(pm25: float) -> float:
    if pd.isna(pm25) or pm25 < 0: return float("nan")
    for c_low, c_high, i_low, i_high in _NAQI_BREAKPOINTS:
        if c_low <= pm25 <= c_high:
            return round(((i_high - i_low) / (c_high - c_low)) * (pm25 - c_low) + i_low, 1)
    return 500.0

output_path = os.path.join("data_store", "cache", "aqi_delhi.csv")
start_date = "2023-01-01"
end_date = "2024-12-31"

all_station_data = []

for station_name, coords in DELHI_STATIONS.items():
    lat, lon = coords["lat"], coords["lon"]
    print(f"Fetching {station_name}...")
    url = (f"https://air-quality-api.open-meteo.com/v1/air-quality"
           f"?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
           f"&hourly=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone")
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        hourly = resp.json().get("hourly", {})
        if not hourly: continue
        
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(hourly.get("time")),
            "station": station_name,
            "lat": lat, "lon": lon,
            "pm25": hourly.get("pm2_5"),
            "pm10": hourly.get("pm10"),
            "co": hourly.get("carbon_monoxide"),
            "no2": hourly.get("nitrogen_dioxide"),
            "so2": hourly.get("sulphur_dioxide"),
            "o3": hourly.get("ozone")
        })
        df["aqi"] = df["pm25"].apply(calculate_aqi_from_pm25)
        all_station_data.append(df)
        time.sleep(1)
    except Exception as e:
        print(f"Failed {station_name}: {e}")

if all_station_data:
    new_df = pd.concat(all_station_data, ignore_index=True)
    existing_df = pd.read_csv(output_path)
    final_df = pd.concat([existing_df, new_df], ignore_index=True)
    final_df.to_csv(output_path, index=False)
    print(f"Successfully appended {len(new_df)} rows for Punjabi Bagh and Shadipur.")
else:
    print("Could not fetch the missing stations.")
