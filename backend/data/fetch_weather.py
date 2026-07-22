import requests
import pandas as pd
import os

DELHI_LAT, DELHI_LON = 28.6139, 77.2090

def fetch_weather(start_date, end_date):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": DELHI_LAT,
        "longitude": DELHI_LON,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,surface_pressure,precipitation",
        "timezone": "Asia/Kolkata"
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()["hourly"]
    return pd.DataFrame(data)

if __name__ == "__main__":
    df = fetch_weather("2023-01-01", "2024-12-31")
    os.makedirs("data/raw", exist_ok=True)
    df.to_csv("data/raw/weather_delhi.csv", index=False)
    print(f"Saved {len(df)} records to data/raw/weather_delhi.csv")
