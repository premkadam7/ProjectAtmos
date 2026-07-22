import os
import joblib
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta, timezone

_models = {}
_feature_names = None
_latest_features = None

def _load_resources():
    global _models, _feature_names, _latest_features
    if _models:
        return

    model_dir = os.path.join(os.path.dirname(__file__), "..", "data_store", "models")
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "data_store", "cache")

    try:
        _models['q10'] = joblib.load(os.path.join(model_dir, "champion_q10.pkl"))
        _models['q50'] = joblib.load(os.path.join(model_dir, "champion_q50.pkl"))
        _models['q90'] = joblib.load(os.path.join(model_dir, "champion_q90.pkl"))
        _feature_names = joblib.load(os.path.join(model_dir, "feature_names.pkl"))

        df = pd.read_csv(os.path.join(cache_dir, "features_delhi.csv"))
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").groupby("station").tail(1).reset_index(drop=True)
        _latest_features = df
    except Exception as e:
        print(f"Failed to load models: {e}")

from data.ingest import calculate_aqi_from_pm25

def _pm25_to_aqi(pm25):
    """Accurate NAQI breakpoints scale."""
    return calculate_aqi_from_pm25(pm25)

def get_city_overview():
    _load_resources()
    if _latest_features is None:
        return []

    overview = []
    for _, row in _latest_features.iterrows():
        ward_id = row.get("ward_id", "unknown")
        if pd.isna(ward_id):
            continue

        wf = get_ward_forecast(ward_id, 72)
        if not wf:
            continue

        current_aqi = wf["current_aqi"]
        hourly = wf["hourly"]
        
        # 24h, 48h, 72h forecasts from the hourly list
        f_24h = hourly[23]["aqi"]
        f_48h = hourly[47]["aqi"]
        f_72h = hourly[71]["aqi"]

        overview.append({
            "ward_id": ward_id,
            "ward_name": wf["ward_name"],
            "lat": row.get("lat", 28.6139),
            "lon": row.get("lon", 77.2090),
            "current_aqi": current_aqi,
            "forecast_aqi_24h": f_24h,
            "forecast_aqi_48h": f_48h,
            "forecast_aqi_72h": f_72h,
            "trend": "worsening" if f_24h > current_aqi else "improving",
            "cigarette_equivalent": wf["cigarette_equivalent"]
        })
    return overview

def get_ward_forecast(ward_id: str, hours: int = 72):
    _load_resources()
    if _latest_features is None:
        return None

    ward_row = _latest_features[_latest_features["ward_id"] == ward_id]
    if ward_row.empty:
        ward_row = _latest_features.iloc[[0]]

    row = ward_row.iloc[0]
    current_pm25 = row.get("pm25", 50.0)
    current_aqi = _pm25_to_aqi(current_pm25)

    X = row[_feature_names].values.reshape(1, -1)
    q10_24h = _pm25_to_aqi(_models['q10'].predict(X)[0])
    q50_24h = _pm25_to_aqi(_models['q50'].predict(X)[0])
    q90_24h = _pm25_to_aqi(_models['q90'].predict(X)[0])

    hourly = []
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    delta_per_hour = (q50_24h - current_aqi) / 24.0

    for i in range(hours):
        if i <= 24:
            base = current_aqi + delta_per_hour * i
        else:
            base = q50_24h + delta_per_hour * (i - 24) * 0.5

        hour_of_day = (now.hour + i) % 24
        diurnal = 15 * (
            math.cos((hour_of_day - 9) * math.pi / 12)
            + math.cos((hour_of_day - 20) * math.pi / 12)
        )

        aqi = max(10.0, base + diurnal)

        uncertainty = min(1.0, i / 24.0)
        band = (q90_24h - q10_24h) * uncertainty

        hourly.append({
            "timestamp": (now + timedelta(hours=i)).isoformat(),
            "aqi": round(aqi, 1),
            "pm25": round(aqi * 0.5, 1),
            "pm10": round(aqi * 0.8, 1),
            "aqi_low": round(aqi - band / 2, 1),
            "aqi_high": round(aqi + band / 2, 1)
        })

    return {
        "ward_id": row.get("ward_id"),
        "ward_name": row.get("station"),
        "current_aqi": round(current_aqi, 1),
        "cigarette_equivalent": round(current_pm25 / 22.0, 1),
        "hourly": hourly
    }

_shap_explainer = None

def get_ward_blame(ward_id: str):
    import shap
    global _shap_explainer

    _load_resources()
    if _latest_features is None or _models.get('q50') is None:
        return None

    if _shap_explainer is None:
        _shap_explainer = shap.TreeExplainer(_models['q50'])

    ward_row = _latest_features[_latest_features["ward_id"] == ward_id]
    if ward_row.empty:
        ward_row = _latest_features.iloc[[0]]

    row = ward_row.iloc[0]
    X = row[_feature_names].values.reshape(1, -1)
    shap_values = _shap_explainer.shap_values(X)[0]

    weather_feats = {
        'temperature_2m', 'relative_humidity_2m', 'wind_speed_10m',
        'wind_direction_10m', 'surface_pressure', 'precipitation',
        'wind_humidity_cross', 'temp_wind_cross'
    }
    temporal_feats = {
        'hour', 'day_of_week', 'is_weekend', 'hour_sin', 'hour_cos',
        'month_sin', 'month_cos', 'dow_sin', 'dow_cos',
        'is_diwali', 'is_new_year', 'is_stubble_season', 'month'
    }
    spatial_feats = {'ndvi_mean', 'population_density_per_km2'}

    categories = {
        "Weather": {"icon": "🌦️", "score": 0.0},
        "Traffic & Time": {"icon": "🚗", "score": 0.0},
        "Historical / Baseline": {"icon": "🏭", "score": 0.0},
        "Geography & Infra": {"icon": "🌳", "score": 0.0},
        "Other": {"icon": "❓", "score": 0.0},
    }

    baseline_feats = {c for c in _feature_names if any(k in c for k in ['lag', 'rolling', 'pm', 'aqi', 'no2', 'co'])}

    for i, feat in enumerate(_feature_names):
        val = abs(shap_values[i])
        if feat in weather_feats:
            categories["Weather"]["score"] += val
        elif feat in temporal_feats:
            categories["Traffic & Time"]["score"] += val
        elif feat in baseline_feats:
            categories["Historical / Baseline"]["score"] += val
        elif feat in spatial_feats:
            categories["Geography & Infra"]["score"] += val
        else:
            categories["Other"]["score"] += val

    total = sum(c["score"] for c in categories.values()) or 1.0

    factors = []
    for name, info in categories.items():
        if info["score"] > 0:
            factors.append({
                "name": name,
                "icon": info["icon"],
                "percentage": float(round(info["score"] / total * 100, 1)),
                "shap_value": float(round(info["score"], 2))
            })

    factors.sort(key=lambda x: x["percentage"], reverse=True)

    top = factors[0] if factors else {"name": "Unknown", "percentage": 0}

    current_pm25 = float(row.get("pm25", 50.0))
    pred_pm25 = float(_models['q50'].predict(X)[0])

    return {
        "ward_id": str(row.get("ward_id", ward_id)),
        "ward_name": str(row.get("station", ward_id)),
        "current_aqi": float(round(_pm25_to_aqi(current_pm25), 1)),
        "factors": factors,
        "explanation": f"AQI is primarily influenced by {top['name']} ({top['percentage']}%).",
        "forecast_trend": "worsening" if pred_pm25 > current_pm25 else "improving"
    }


def run_whatif_simulation(ward_id: str, intervention: str, duration_hours: int = 48) -> dict:
    _load_resources()
    if _latest_features is None or _models.get('q50') is None:
        return {}

    # Find the ward row
    ward_row = _latest_features[_latest_features["ward_id"] == ward_id]
    if ward_row.empty:
        ward_row = _latest_features.iloc[[0]]

    row = ward_row.iloc[0]
    ward_name = row.get("station", ward_id)

    # 1. Baseline prediction
    X = row[_feature_names].values.reshape(1, -1)
    baseline_pm25 = _models['q50'].predict(X)[0]
    baseline_aqi = _pm25_to_aqi(baseline_pm25)

    # 3. Production mode (genuine ML counterfactual)
    modified_row = row.copy()
    if intervention == "pause_construction":
        modified_row["pm10"] = 0.0
    elif intervention == "restrict_traffic":
        modified_row["no2"] = 0.0
        modified_row["co"] = 0.0
    elif intervention in ("industrial_shutdown", "pause factory industrial emissions"):
        modified_row["so2"] = 0.0

    X_mod = modified_row[_feature_names].values.reshape(1, -1)
    counterfactual_pm25 = _models['q50'].predict(X_mod)[0]
    counterfactual_aqi = _pm25_to_aqi(counterfactual_pm25)

    scale = 1.0 - math.exp(-duration_hours / 24.0)
    with_intervention = baseline_aqi - (max(0.0, baseline_aqi - counterfactual_aqi) * scale)
    reduction = baseline_aqi - with_intervention
    reduction_percentage = (reduction / baseline_aqi) * 100.0 if baseline_aqi > 0 else 0.0

    return {
        "ward_id": ward_id,
        "ward_name": str(ward_name),
        "intervention": intervention,
        "duration_hours": duration_hours,
        "current_forecast": round(float(baseline_aqi), 1),
        "with_intervention": round(float(with_intervention), 1),
        "reduction": round(float(reduction), 1),
        "reduction_percentage": round(float(reduction_percentage), 1)
    }

