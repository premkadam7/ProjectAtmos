import pandas as pd
import numpy as np
import os
import sys
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NCR stations that fall outside Delhi municipal boundaries
NCR_STATIONS = {
    "Noida Sector 62", "Greater Noida", "Gurgaon Vikas Sadan",
    "Faridabad", "Ghaziabad Vasundhara"
}

def _normalize_ward_name(name: str) -> str:
    return re.sub(r'\s+', '_', str(name).strip()).lower()

def engineer_features():
    cache_dir = os.path.join("data_store", "cache")
    aqi_path = os.path.join(cache_dir, "aqi_delhi.csv")
    weather_path = os.path.join(cache_dir, "weather_delhi.csv")
    output_path = os.path.join(cache_dir, "features_delhi.csv")

    if not os.path.exists(aqi_path) or not os.path.exists(weather_path):
        logger.error("Missing raw data files. Run ingest.py first.")
        sys.exit(1)

    logger.info("Loading datasets")
    df_aqi = pd.read_csv(aqi_path)
    df_weather = pd.read_csv(weather_path)

    before = len(df_aqi)
    df_aqi = df_aqi[~df_aqi["station"].isin(NCR_STATIONS)].reset_index(drop=True)
    logger.info(f"Dropped {before - len(df_aqi)} NCR rows")

    df_aqi["timestamp"] = pd.to_datetime(df_aqi["timestamp"])
    df_weather["time"] = pd.to_datetime(df_weather["time"])
    df_weather.rename(columns={"time": "timestamp"}, inplace=True)

    df = pd.merge(df_aqi, df_weather, on="timestamp", how="inner")

    df = df.sort_values(by=["station", "timestamp"]).reset_index(drop=True)

    logger.info("Imputing missing values (forward fill, median fallback)")
    cols_to_fill = [
        "pm25", "pm10", "no2", "co", "so2", "o3", "aqi",
        "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
        "wind_direction_10m", "surface_pressure", "precipitation"
    ]

    for col in cols_to_fill:
        if col in df.columns:
            df[col] = df.groupby("station")[col].ffill()
            global_median = df[col].median()
            df[col] = df[col].fillna(global_median if not pd.isna(global_median) else 0)

    logger.info("Temporal features")
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    # Cyclical encodings so the model sees Dec/Jan and Sun/Mon as adjacent
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

    df["is_stubble_season"] = df["month"].isin([9, 10, 11, 12]).astype(int)

    diwali_2023 = pd.to_datetime("2023-11-12")
    diwali_2024 = pd.to_datetime("2024-10-31")
    is_diwali_23 = (df["timestamp"] >= (diwali_2023 - pd.Timedelta(days=2))) & (df["timestamp"] <= (diwali_2023 + pd.Timedelta(days=2)))
    is_diwali_24 = (df["timestamp"] >= (diwali_2024 - pd.Timedelta(days=2))) & (df["timestamp"] <= (diwali_2024 + pd.Timedelta(days=2)))
    df["is_diwali"] = (is_diwali_23 | is_diwali_24).astype(int)

    is_dec31 = (df["month"] == 12) & (df["timestamp"].dt.day == 31)
    is_jan1 = (df["month"] == 1) & (df["timestamp"].dt.day == 1)
    df["is_new_year"] = (is_dec31 | is_jan1).astype(int)

    logger.info("Engineering lag features")
    lags = [1, 3, 6, 12, 24]
    for lag in lags:
        df[f"pm25_lag_{lag}h"] = df.groupby("station")["pm25"].shift(lag)
        if "aqi" in df.columns:
            df[f"aqi_lag_{lag}h"] = df.groupby("station")["aqi"].shift(lag)

    logger.info("Rolling features")
    windows = [6, 12, 24]
    for w in windows:
        df[f"pm25_rolling_{w}h"] = df.groupby("station")["pm25"].transform(
            lambda x: x.rolling(w, min_periods=w).mean()
        )
        if "aqi" in df.columns:
            df[f"aqi_rolling_{w}h"] = df.groupby("station")["aqi"].transform(
                lambda x: x.rolling(w, min_periods=w).mean()
            )

    logger.info("Interaction features")
    if "wind_speed_10m" in df.columns and "relative_humidity_2m" in df.columns:
        df["wind_humidity_cross"] = df["wind_speed_10m"] * df["relative_humidity_2m"]

    if "temperature_2m" in df.columns and "wind_speed_10m" in df.columns:
        df["temp_wind_cross"] = df["temperature_2m"] / (df["wind_speed_10m"] + 1)

    logger.info("Spatial ward assignment")
    try:
        import boundaries
        station_coords = df[["station", "lat", "lon"]].drop_duplicates()
        ward_map = {}
        for _, row in station_coords.iterrows():
            ward_info = boundaries.get_ward_by_coords(row["lat"], row["lon"])
            if ward_info and ward_info.get("name") != "Unknown":
                ward_map[row["station"]] = _normalize_ward_name(ward_info["name"])
            else:
                ward_map[row["station"]] = "unknown"

        df["ward_id"] = df["station"].map(ward_map)
    except ImportError:
        logger.warning("boundaries module not found, skipping spatial join")
    except Exception as e:
        logger.warning(f"Spatial join failed: {e}")

    ndvi_path = os.path.join(cache_dir, "delhi_wards_ndvi.csv")
    if os.path.exists(ndvi_path):
        logger.info("Merging NDVI data")
        df_ndvi = pd.read_csv(ndvi_path)
        df_ndvi["ward_id"] = df_ndvi["Ward_Name"].apply(_normalize_ward_name)
        df_ndvi = df_ndvi.drop(columns=["Ward_Name"], errors='ignore')
        df = pd.merge(df, df_ndvi, on="ward_id", how="left")
        if "ndvi_mean" in df.columns:
            df["ndvi_mean"] = df["ndvi_mean"].fillna(0.0)

    pop_path = os.path.join(cache_dir, "delhi_wards_population.csv")
    if os.path.exists(pop_path):
        logger.info("Merging population density data")
        df_pop = pd.read_csv(pop_path)
        df_pop["ward_id"] = df_pop["ward_name"].apply(_normalize_ward_name)
        df_pop = df_pop.drop(columns=["ward_name", "population"], errors='ignore')
        df = pd.merge(df, df_pop, on="ward_id", how="left")
        if "population_density_per_km2" in df.columns:
            global_pop_median = df["population_density_per_km2"].median()
            df["population_density_per_km2"] = df["population_density_per_km2"].fillna(
                global_pop_median if not pd.isna(global_pop_median) else 0.0
            )

    # Drop rows with NaNs from lag/rolling (first 24h per station)
    df = df.dropna().reset_index(drop=True)

    logger.info(f"Final feature matrix: {df.shape}")

    df.to_csv(output_path, index=False)
    logger.info(f"Exported to {output_path}")

if __name__ == "__main__":
    engineer_features()
