import pandas as pd
import requests
import os
import time

DELHI_STATIONS = {
    "Anand Vihar": {"lat": 28.6469, "lon": 77.3164},
    "Ashok Vihar": {"lat": 28.6952, "lon": 77.1811},
    "Bawana": {"lat": 28.7762, "lon": 77.0513},
    "CRRI Mathura Road": {"lat": 28.5513, "lon": 77.2736},
    "DTU": {"lat": 28.7500, "lon": 77.1113},
    "Dwarka Sector 8": {"lat": 28.5708, "lon": 77.0711},
    "IGI Airport T3": {"lat": 28.5627, "lon": 77.1180},
    "ITO": {"lat": 28.6289, "lon": 77.2406},
    "Jahangirpuri": {"lat": 28.7327, "lon": 77.1707},
    "JLN Stadium": {"lat": 28.5833, "lon": 77.2425},
    "Lodhi Road": {"lat": 28.5918, "lon": 77.2273},
    "Mandir Marg": {"lat": 28.6364, "lon": 77.2008},
    "Mundka": {"lat": 28.6839, "lon": 77.0318},
    "NSIT Dwarka": {"lat": 28.6090, "lon": 77.0323},
    "Najafgarh": {"lat": 28.5703, "lon": 76.9337},
    "Narela": {"lat": 28.8229, "lon": 77.1025},
    "Nehru Nagar": {"lat": 28.5676, "lon": 77.2507},
    "North Campus DU": {"lat": 28.6879, "lon": 77.2097},
    "Okhla Phase 2": {"lat": 28.5308, "lon": 77.2713},
    "Patparganj": {"lat": 28.6237, "lon": 77.2877},
    "Punjabi Bagh": {"lat": 28.6741, "lon": 77.1310},
    "Pusa IMD": {"lat": 28.6396, "lon": 77.1463},
    "R K Puram": {"lat": 28.5631, "lon": 77.1727},
    "Rohini": {"lat": 28.7324, "lon": 77.1196},
    "Shadipur": {"lat": 28.6515, "lon": 77.1588},
    "Siri Fort": {"lat": 28.5505, "lon": 77.2156},
    "Sonia Vihar": {"lat": 28.7105, "lon": 77.2494},
    "Vivek Vihar": {"lat": 28.6725, "lon": 77.3152},
    "Wazirpur": {"lat": 28.6997, "lon": 77.1654},
    "Noida Sector 62": {"lat": 28.6263, "lon": 77.3571},
    "Greater Noida": {"lat": 28.4744, "lon": 77.5040},
    "Gurgaon Vikas Sadan": {"lat": 28.4501, "lon": 77.0263},
    "Faridabad": {"lat": 28.4089, "lon": 77.3178},
    "Ghaziabad Vasundhara": {"lat": 28.6603, "lon": 77.3573},
}

# Indian NAQI breakpoints for PM2.5 (µg/m³)
_NAQI_BREAKPOINTS = [
    (0, 30, 0, 50),
    (31, 60, 51, 100),
    (61, 90, 101, 200),
    (91, 120, 201, 300),
    (121, 250, 301, 400),
    (250, 500, 401, 500),
]

def calculate_aqi_from_pm25(pm25: float) -> float:
    if pd.isna(pm25) or pm25 < 0:
        return float("nan")
    for c_low, c_high, i_low, i_high in _NAQI_BREAKPOINTS:
        if c_low <= pm25 <= c_high:
            return round(((i_high - i_low) / (c_high - c_low)) * (pm25 - c_low) + i_low, 1)
    return 500.0

def fetch_real_aqi_data():
    output_path = os.path.join("data_store", "cache", "aqi_delhi.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    start_date = "2023-01-01"
    end_date = "2024-12-31"

    all_station_data = []

    for i, (station_name, coords) in enumerate(DELHI_STATIONS.items(), 1):
        lat, lon = coords["lat"], coords["lon"]
        print(f"[{i}/{len(DELHI_STATIONS)}] {station_name}...")

        url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}"
            f"&start_date={start_date}&end_date={end_date}"
            f"&hourly=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"
        )

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            hourly = resp.json().get("hourly", {})
            if not hourly:
                continue

            df = pd.DataFrame({
                "timestamp": pd.to_datetime(hourly.get("time")),
                "station": station_name,
                "lat": lat,
                "lon": lon,
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
            print(f"  Failed: {e}")

    if all_station_data:
        final_df = pd.concat(all_station_data, ignore_index=True)
        final_df.to_csv(output_path, index=False)
        print(f"\nSaved {len(final_df)} rows to {output_path}")
        print(f"PM2.5 range: {final_df['pm25'].min():.1f} – {final_df['pm25'].max():.1f}")
    else:
        print("No data fetched.")

if __name__ == "__main__":
    fetch_real_aqi_data()
