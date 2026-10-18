import math
import threading

import pandas as pd

from data.ingest import calculate_aqi_from_pm25
from services.live_pipeline import freshness, get_snapshot, model_predict, POLLUTANTS


def _pm25_to_aqi(pm25):
    """Accurate NAQI breakpoints scale."""
    return calculate_aqi_from_pm25(pm25)


class UnknownWardError(LookupError):
    """A ward_id that no monitored station belongs to (served as HTTP 404)."""

    def __init__(self, ward_id):
        super().__init__(ward_id)
        self.ward_id = ward_id


class UnsupportedInterventionError(ValueError):
    """An intervention the what-if model has no counterfactual for (HTTP 422)."""


# Features zeroed for each intervention's counterfactual (sensitivity analysis)
INTERVENTION_FEATURES = {
    "pause_construction": ["pm10"],
    "restrict_traffic": ["no2", "co"],
    "industrial_shutdown": ["so2"],
}
INTERVENTION_ALIASES = {"pause factory industrial emissions": "industrial_shutdown"}


def _find_ward(snap, ward_id):
    for w in snap["wards"]:
        if w["ward_id"] == ward_id:
            return w
    raise UnknownWardError(ward_id)


def _latest_row(ward_id):
    """Latest model feature row for a ward."""
    latest = get_snapshot()["latest_features"]
    ward_row = latest[latest["ward_id"] == ward_id]
    if ward_row.empty:
        raise UnknownWardError(ward_id)
    return ward_row.iloc[0]


def get_data_source():
    snap = get_snapshot()
    return {
        "data_source": snap["source"],
        "source_detail": snap["source_detail"],
        "observed_at": snap["observed_at"],
        "generated_at": snap["generated_at"],
        "ground_stations": snap["ground_stations"],
        "freshness": freshness(snap),
    }


def get_city_overview():
    snap = get_snapshot()
    return [{k: v for k, v in w.items() if k != "hourly"} for w in snap["wards"]]


def get_city_hourly():
    """Hourly AQI predictions for every ward, for the map timeline."""
    snap = get_snapshot()
    if not snap["wards"]:
        return {"timestamps": [], "wards": {}}
    return {
        "timestamps": [h["timestamp"] for h in snap["wards"][0]["hourly"]],
        "wards": {w["ward_id"]: [h["aqi"] for h in w["hourly"]] for w in snap["wards"]},
    }


def get_ward_forecast(ward_id: str, hours: int = 72):
    w = _find_ward(get_snapshot(), ward_id)
    return {
        "ward_id": w["ward_id"],
        "ward_name": w["ward_name"],
        "current_aqi": w["current_aqi"],
        "current_pm25": w["current_pm25"],
        "cigarette_equivalent": w["cigarette_equivalent"],
        "hourly": w["hourly"][:hours],
    }


HISTORY_SERIES_INFO = {
    "kind": "modelled",
    "description": "CAMS atmospheric model estimates (via Open-Meteo) at station locations, "
                   "not station measurements and not calibrated to CPCB readings",
}


def get_history(ward_id: str = None, hours: int = 24 * 30):
    """Hourly modelled pollutant history for one ward, or the city mean when ward_id is None."""
    hist = get_snapshot()["history"]
    if ward_id:
        hist = hist[hist["ward_id"] == ward_id]
        if hist.empty:
            raise UnknownWardError(ward_id)
    cols = [*POLLUTANTS, "aqi"]
    series = hist.groupby("timestamp")[cols].mean().sort_index()
    series = series[series.index > series.index.max() - pd.Timedelta(hours=hours)]
    return [
        {"timestamp": ts.tz_localize("UTC").isoformat(), **{c: round(float(row[c]), 2) for c in cols}}
        for ts, row in series.iterrows()
    ]


_shap_explainer = None
_shap_lock = threading.Lock()


def _model_resources():
    from services.live_pipeline import _load_resources
    res = _load_resources()
    return res["models"], res["feature_names"]


def get_ward_blame(ward_id: str):
    import shap
    global _shap_explainer

    models, feature_names = _model_resources()
    if _shap_explainer is None:
        with _shap_lock:
            if _shap_explainer is None:
                _shap_explainer = shap.TreeExplainer(models['q50'])

    row = _latest_row(ward_id)
    X = row[feature_names].values.astype(float).reshape(1, -1)
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

    baseline_feats = {c for c in feature_names if any(k in c for k in ['lag', 'rolling', 'pm', 'aqi', 'no2', 'co'])}

    for i, feat in enumerate(feature_names):
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

    ward = _find_ward(get_snapshot(), row["ward_id"])

    return {
        "ward_id": str(row.get("ward_id", ward_id)),
        "ward_name": str(row.get("station", ward_id)),
        "current_aqi": float(ward["current_aqi"]),
        "factors": factors,
        "explanation": f"AQI is primarily influenced by {top['name']} ({top['percentage']}%).",
        "forecast_trend": ward["trend"]
    }


def run_whatif_simulation(ward_id: str, intervention: str, duration_hours: int = 48) -> dict:
    key = INTERVENTION_ALIASES.get(intervention, intervention)
    if key not in INTERVENTION_FEATURES:
        raise UnsupportedInterventionError(
            f"Unsupported intervention '{intervention}'. Supported: {', '.join(INTERVENTION_FEATURES)}"
        )
    models, feature_names = _model_resources()
    row = _latest_row(ward_id)
    ward_name = row.get("station", ward_id)
    # Model output is on the CAMS scale; the station ratio maps it to ground level
    ratio = float(row.get("ratio_pm25", 1.0))

    # 1. Baseline prediction
    X = row[feature_names].values.astype(float).reshape(1, -1)
    baseline_pm25 = model_predict(models['q50'], X)[0] * ratio
    baseline_aqi = _pm25_to_aqi(baseline_pm25)

    # 3. Production mode (genuine ML counterfactual)
    modified_row = row.copy()
    for feature in INTERVENTION_FEATURES[key]:
        modified_row[feature] = 0.0

    X_mod = modified_row[feature_names].values.astype(float).reshape(1, -1)
    counterfactual_pm25 = model_predict(models['q50'], X_mod)[0] * ratio
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

