"""Live data ingestion and model inference.

Every refresh builds a *snapshot*: per-station 72h forecasts, recent history and
the latest feature rows. API endpoints read the snapshot instead of recomputing,
so requests stay fast.

Data flow for a live snapshot:
  1. Open-Meteo air-quality (CAMS) hourly history + short-range forecast for each
     model station, and Open-Meteo weather. These are the same sources the model
     was trained on, so the model sees inputs from its training distribution.
  2. LightGBM quantile models predict PM2.5 24h ahead from each of the last 24
     hourly feature rows (horizons +1..+24h), then recursively for +25..+72h
     using their own median predictions as lag inputs.
  3. CPCB ground readings (via WAQI) calibrate each station: CAMS underestimates
     Delhi PM2.5, so predictions are scaled by the station's observed/modelled
     ratio and the first hours are anchored to the current observation.

If the live sources are unreachable the snapshot falls back to the bundled
sample dataset (Dec 2024) and is labelled as such.
"""
import logging
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from filelock import FileLock
from services.input_cache import atomic_pickle, read_pickle, request_json, incremental_frame

import joblib
import numpy as np
import pandas as pd
import requests

from data.ingest import calculate_aqi_from_pm25
from data.preprocess import add_model_features

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_DIR = os.path.join(BACKEND_DIR, "data_store", "models")
CACHE_DIR = os.path.join(BACKEND_DIR, "data_store", "cache")
RUNTIME_DIR = os.getenv("ATMOS_CACHE_DIR", os.path.join(CACHE_DIR, "runtime"))
SNAPSHOT_PATH = os.path.join(RUNTIME_DIR, "live_snapshot.pkl")

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
WAQI_URL = "https://api.waqi.info"

# lat1,lon1,lat2,lon2 box around Delhi NCT for the WAQI station search
DELHI_BOUNDS = "28.40,76.83,28.89,77.35"

AQ_VARS = {
    "pm2_5": "pm25", "pm10": "pm10", "carbon_monoxide": "co",
    "nitrogen_dioxide": "no2", "sulphur_dioxide": "so2", "ozone": "o3",
}
POLLUTANTS = list(AQ_VARS.values())
WEATHER_VARS = [
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
    "wind_direction_10m", "surface_pressure", "precipitation",
]
RAW_COLUMNS = ["timestamp", "station", "lat", "lon", *POLLUTANTS, "aqi", *WEATHER_VARS]
STATIC_COLUMNS = ["ward_id", "ndvi_mean", "population_density_per_km2"]

HORIZON_HOURS = 72
MODEL_LEAD_HOURS = 24          # the models predict PM2.5 this many hours ahead
ANCHOR_HALF_LIFE_HOURS = 6     # how quickly the forecast hands over from observation to model
GROUND_MATCH_KM = 1.5    # model stations sit on CPCB monitor sites, so true matches are close
GROUND_MAX_AGE_HOURS = 3
RATIO_BOUNDS = (0.25, 4.0)
LIVE_ENABLED = os.getenv("ATMOS_LIVE", "1") != "0"
REFRESH_SECONDS = int(os.getenv("ATMOS_REFRESH_MINUTES", "30")) * 60
FIRST_LIVE_WAIT_SECONDS = 20
# Live observations older than this are reported as stale (refreshes failing)
STALE_AFTER_MINUTES = int(os.getenv("ATMOS_STALE_AFTER_MINUTES", "120"))

# US EPA AQI breakpoints (concentration low/high, index low/high); WAQI reports
# station sub-indices on this scale, so they are inverted back to µg/m³.
_EPA_PM25 = [
    (0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]
_EPA_PM10 = [
    (0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150), (255, 354, 151, 200),
    (355, 424, 201, 300), (425, 504, 301, 400), (505, 604, 401, 500),
]


# ── Static resources ────────────────────────────────────────────────────────

_resources = None
_resources_lock = threading.Lock()


def _load_resources():
    """Models and static station data, loaded once.

    The bundle is built completely before it is published, so concurrent
    callers (refresh thread, warm-up, requests) never see a partial one.
    """
    global _resources
    if _resources is not None:
        return _resources
    with _resources_lock:
        if _resources is None:
            models = {
                q: joblib.load(os.path.join(MODEL_DIR, f"champion_{q}.pkl")) for q in ("q10", "q50", "q90")
            }
            feature_names = joblib.load(os.path.join(MODEL_DIR, "feature_names.pkl"))
            sample = pd.read_csv(os.path.join(CACHE_DIR, "features_delhi.csv"))
            sample["timestamp"] = pd.to_datetime(sample["timestamp"])
            stations = sample.groupby("station", as_index=False)[["lat", "lon", *STATIC_COLUMNS]].first()
            _resources = {
                "models": models,
                "feature_names": feature_names,
                "sample": sample,
                "stations": stations,
            }
    return _resources


# ── Fetching ────────────────────────────────────────────────────────────────

def fetch_air_quality(stations: pd.DataFrame, past_days: int = 3) -> pd.DataFrame:
    """Hourly CAMS pollutants (UTC labels), with five calendar days of forecast."""
    params = {
        "latitude": ",".join(f"{v:.4f}" for v in stations["lat"]),
        "longitude": ",".join(f"{v:.4f}" for v in stations["lon"]),
        "hourly": ",".join(AQ_VARS),
        "past_days": past_days,
        "forecast_days": 5,
        "timezone": "GMT",
    }
    payload = request_json(AQ_URL, params, RUNTIME_DIR)
    if isinstance(payload, dict):
        payload = [payload]

    if len(payload) != len(stations):
        raise RuntimeError("Air-quality provider returned incomplete station coverage")
    frames = []
    for st, loc in zip(stations.itertuples(), payload):
        hourly = loc["hourly"]
        df = pd.DataFrame({src_dst: hourly[src] for src, src_dst in AQ_VARS.items()})
        df.insert(0, "timestamp", pd.to_datetime(hourly["time"]))
        df.insert(1, "station", st.station)
        df.insert(2, "lat", st.lat)
        df.insert(3, "lon", st.lon)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def fetch_weather(past_days: int = 3) -> pd.DataFrame:
    """City-centre hourly weather aligned to the UTC pollutant timestamps."""
    params = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "hourly": ",".join(WEATHER_VARS),
        "past_days": past_days,
        "forecast_days": 5,
        "timezone": "GMT",
    }
    hourly = request_json(WEATHER_URL, params, RUNTIME_DIR)["hourly"]
    df = pd.DataFrame({v: hourly[v] for v in WEATHER_VARS})
    df.insert(0, "timestamp", pd.to_datetime(hourly["time"]))
    return df


def _epa_aqi_to_concentration(aqi, table):
    if aqi is None:
        return None
    try:
        aqi = float(aqi)
    except (TypeError, ValueError):
        return None
    for c_low, c_high, i_low, i_high in table:
        if aqi <= i_high:
            return c_low + (aqi - max(i_low, 0)) * (c_high - c_low) / (i_high - i_low)
    return table[-1][1]


def _fetch_waqi_feed(uid, token):
    resp = requests.get(f"{WAQI_URL}/feed/@{uid}/", params={"token": token}, timeout=15)
    resp.raise_for_status()
    body = resp.json()
    return body.get("data") if body.get("status") == "ok" else None


def fetch_ground_stations(token: str) -> pd.DataFrame:
    """Current CPCB/DPCC station readings in Delhi from WAQI, as µg/m³."""
    resp = requests.get(
        f"{WAQI_URL}/map/bounds",
        params={"latlng": DELHI_BOUNDS, "networks": "all", "token": token},
        timeout=20,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != "ok":
        raise RuntimeError(f"WAQI error: {body.get('data')}")

    uids = [s["uid"] for s in body.get("data", []) if s.get("uid") is not None]
    with ThreadPoolExecutor(max_workers=8) as pool:
        feeds = list(pool.map(lambda uid: _safe(_fetch_waqi_feed, uid, token), uids))

    now = datetime.now(timezone.utc)
    rows = []
    for feed in feeds:
        if not feed:
            continue
        iaqi = feed.get("iaqi", {})
        pm25 = _epa_aqi_to_concentration(iaqi.get("pm25", {}).get("v"), _EPA_PM25)
        if pm25 is None:
            continue
        observed = pd.to_datetime(feed.get("time", {}).get("iso"), utc=True, errors="coerce")
        if pd.isna(observed) or not -300 <= (now - observed).total_seconds() <= GROUND_MAX_AGE_HOURS * 3600:
            continue
        geo = feed.get("city", {}).get("geo") or [None, None]
        rows.append({
            "name": feed.get("city", {}).get("name", ""),
            "lat": float(geo[0]),
            "lon": float(geo[1]),
            "pm25": pm25,
            "pm10": _epa_aqi_to_concentration(iaqi.get("pm10", {}).get("v"), _EPA_PM10),
            "observed_at": observed,
        })
    return pd.DataFrame(rows)


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        logger.warning("WAQI feed failed: %s", e)
        return None


# ── Calibration ─────────────────────────────────────────────────────────────

def _haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def calibrate(stations: pd.DataFrame, cams_now: pd.DataFrame, ground: pd.DataFrame) -> pd.DataFrame:
    """Per-station observed/modelled ratios for PM2.5 and PM10.

    Stations with a CPCB monitor within GROUND_MATCH_KM use its reading directly;
    others get an inverse-distance-weighted ratio from the matched stations.
    """
    out = stations[["station", "lat", "lon"]].merge(
        cams_now[["station", "pm25", "pm10"]].rename(columns={"pm25": "cams_pm25", "pm10": "cams_pm10"}),
        on="station",
    )
    out["ratio_pm25"] = np.nan
    out["ratio_pm10"] = np.nan
    out["ground_station"] = None
    out["ground_observed_at"] = None

    if ground is not None and not ground.empty:
        for i, st in out.iterrows():
            dist = _haversine_km(st.lat, st.lon, ground["lat"].values, ground["lon"].values)
            j = int(np.argmin(dist))
            if dist[j] <= GROUND_MATCH_KM:
                g = ground.iloc[j]
                out.at[i, "ratio_pm25"] = g.pm25 / max(st.cams_pm25, 1.0)
                if g.pm10 is not None and not pd.isna(g.pm10):
                    out.at[i, "ratio_pm10"] = g.pm10 / max(st.cams_pm10, 1.0)
                out.at[i, "ground_station"] = g["name"]
                out.at[i, "ground_observed_at"] = g["observed_at"].isoformat()

    for col in ("ratio_pm25", "ratio_pm10"):
        out[col] = out[col].clip(*RATIO_BOUNDS)
        known = out[out[col].notna()]
        if known.empty:
            out[col] = out[col].fillna(out["ratio_pm25"] if col == "ratio_pm10" else 1.0).fillna(1.0)
            continue
        for i, st in out[out[col].isna()].iterrows():
            dist = _haversine_km(st.lat, st.lon, known["lat"].values, known["lon"].values)
            w = 1.0 / np.maximum(dist, 0.5) ** 2
            # Average in log space so ratios of 0.5 and 2 balance out
            out.at[i, col] = float(np.exp(np.sum(w * np.log(known[col].values)) / np.sum(w)))
    return out


# ── Feature frame + inference ───────────────────────────────────────────────

def build_frame(raw: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """Impute, compute AQI and engineer model features exactly as preprocess.py does."""
    df = raw.sort_values(["station", "timestamp"]).reset_index(drop=True)
    fill_cols = [*POLLUTANTS, *WEATHER_VARS]
    for col in fill_cols:
        df[col] = df.groupby("station")[col].ffill()
        median = df[col].median()
        df[col] = df[col].fillna(median if not pd.isna(median) else 0)
    df["aqi"] = df["pm25"].apply(calculate_aqi_from_pm25)
    df = add_model_features(df[RAW_COLUMNS])
    return df.merge(stations[["station", *STATIC_COLUMNS]], on="station", how="left")


def model_predict(model, X):
    """Predict with either champion type (LightGBM needs verbose=-1 to stay quiet)."""
    if model.__class__.__module__.startswith("lightgbm"):
        return model.predict(X, verbose=-1)
    return model.predict(X)


def _predict(models, X):
    preds = np.column_stack([model_predict(models[q], X) for q in ("q10", "q50", "q90")])
    preds = np.sort(np.maximum(preds, 0.0), axis=1)   # keep quantiles ordered
    return preds


def forecast_pm25(raw: pd.DataFrame, stations: pd.DataFrame, now: pd.Timestamp):
    """Model PM2.5 quantiles (CAMS scale) for each station for now+1..now+72h.

    Feature rows at times now-23..now give the +1..+24h horizon directly. Their
    median predictions are written back as PM2.5 for those future hours so the
    rows at now+1..now+24 (and then now+25..now+48) can predict further ahead.
    """
    res = _load_resources()
    models, feature_names = res["models"], res["feature_names"]
    lead = pd.Timedelta(hours=MODEL_LEAD_HOURS)
    raw = raw.copy()
    results = []

    for step in range(HORIZON_HOURS // MODEL_LEAD_HOURS):
        frame = build_frame(raw, stations)
        start = now - pd.Timedelta(hours=MODEL_LEAD_HOURS - 1) + step * lead
        end = now + step * lead
        rows = frame[(frame["timestamp"] >= start) & (frame["timestamp"] <= end)]
        preds = _predict(models, rows[feature_names].astype(float))

        step_df = pd.DataFrame({
            "station": rows["station"].values,
            "timestamp": rows["timestamp"].values + np.timedelta64(MODEL_LEAD_HOURS, "h"),
            "q10": preds[:, 0], "q50": preds[:, 1], "q90": preds[:, 2],
        })
        results.append(step_df)

        # Feed the median forecast back in as the PM2.5 "observation" for those hours
        key = raw.set_index(["station", "timestamp"]).index
        upd = step_df.set_index(["station", "timestamp"])["q50"]
        mask = key.isin(upd.index)
        raw.loc[mask, "pm25"] = upd.reindex(key[mask]).values

    return pd.concat(results, ignore_index=True)


def _naqi(pm25):
    return float(calculate_aqi_from_pm25(max(float(pm25), 0.0)))


def assemble_snapshot(raw, stations, now, calib, source, source_detail, ground_count):
    """Turn model output + calibration into the structure the API serves."""
    preds = forecast_pm25(raw, stations, now)
    frame = build_frame(raw, stations)

    calib = calib.set_index("station")
    future_pm10 = raw[raw["timestamp"] > now].set_index(["station", "timestamp"])["pm10"]
    wards = []
    for st in stations.itertuples():
        c = calib.loc[st.station]
        r25, r10 = float(c.ratio_pm25), float(c.ratio_pm10)
        current_pm25 = float(c.cams_pm25) * r25
        current_pm10 = float(c.cams_pm10) * r10
        pm_ratio = current_pm10 / max(current_pm25, 1.0)

        sp = preds[preds["station"] == st.station].sort_values("timestamp")
        hourly = []
        for h, p in enumerate(sp.itertuples(), start=1):
            q10, q50, q90 = p.q10 * r25, p.q50 * r25, p.q90 * r25
            # The first model horizons come from feature rows up to 23h old, so
            # hand over gradually from the current observation to the model.
            w = math.exp(-h * math.log(2) / ANCHOR_HALF_LIFE_HOURS)
            shift = w * (current_pm25 - q50)
            q10, q50, q90 = q10 + shift, q50 + shift, q90 + shift
            pm10 = future_pm10.get((st.station, p.timestamp), np.nan)
            hourly.append({
                "timestamp": pd.Timestamp(p.timestamp).tz_localize("UTC").isoformat(),
                "pm25": round(max(q50, 0.0), 1),
                # Past the CAMS forecast window, scale PM2.5 by the current PM10/PM2.5 ratio
                "pm10": round(float(pm10) * r10 if not pd.isna(pm10) else q50 * pm_ratio, 1),
                "aqi": round(_naqi(q50), 1),
                "aqi_low": round(_naqi(q10), 1),
                "aqi_high": round(_naqi(q90), 1),
            })

        current_aqi = round(_naqi(current_pm25), 1)
        wards.append({
            "ward_id": st.ward_id,
            "ward_name": st.station,
            "lat": float(st.lat),
            "lon": float(st.lon),
            "current_aqi": current_aqi,
            "current_pm25": round(current_pm25, 1),
            "current_pm10": round(current_pm10, 1),
            "forecast_aqi_24h": hourly[23]["aqi"],
            "forecast_aqi_48h": hourly[47]["aqi"],
            "forecast_aqi_72h": hourly[71]["aqi"],
            "trend": "worsening" if hourly[23]["aqi"] > current_aqi else "improving",
            "cigarette_equivalent": round(current_pm25 / 22.0, 1),
            "calibration_ratio": round(r25, 3),
            "ground_station": c.ground_station,
            "ground_observed_at": c.ground_observed_at,
            "estimate_kind": "ground-calibrated" if c.ground_station else ("spatially-calibrated" if ground_count else "regional-model"),
            "hourly": hourly,
        })

    # History up to now: CAMS model estimates exactly as received. Today's
    # calibration ratio is not applied backwards, so past values never change
    # with later calibrations and are never presented as measurements.
    hist = raw[raw["timestamp"] <= now][["timestamp", "station", *POLLUTANTS]].copy()
    hist["aqi"] = hist["pm25"].apply(calculate_aqi_from_pm25)
    hist = hist.merge(
        stations[["station", "ward_id"]], on="station"
    )

    latest = frame[frame["timestamp"] == now].copy()
    latest = latest.merge(calib[["ratio_pm25"]], left_on="station", right_index=True)

    return {
        "source": source,
        "source_detail": source_detail,
        "ground_stations": ground_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "observed_at": pd.Timestamp(now).tz_localize("UTC").isoformat(),
        "wards": wards,
        "history": hist,
        "latest_features": latest.reset_index(drop=True),
    }


# ── Snapshot builders ───────────────────────────────────────────────────────

def build_live_snapshot():
    res = _load_resources()
    stations = res["stations"]

    import hashlib
    signature = hashlib.sha256(stations[["station", "lat", "lon"]].to_csv(index=False).encode()).hexdigest()[:12]
    aq = incremental_frame(os.path.join(RUNTIME_DIR, f"aq-{signature}.pkl"),
                           lambda days: fetch_air_quality(stations, days), ["station", "timestamp"])
    weather = incremental_frame(os.path.join(RUNTIME_DIR, "weather-utc.pkl"),
                                fetch_weather, ["timestamp"])
    # Both providers use UTC. Legacy models need revalidation after correcting
    # the old training alignment; never merge different time zones by clock label.
    raw = aq.merge(weather, on="timestamp", how="inner")
    raw["aqi"] = np.nan

    now = pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None).floor("h")
    needed_end = now + pd.Timedelta(hours=HORIZON_HOURS - MODEL_LEAD_HOURS)
    if raw["timestamp"].max() < needed_end:
        raise RuntimeError("Live data does not extend far enough ahead for the forecast")

    required = pd.date_range(now - pd.Timedelta(hours=48), needed_end, freq="h")
    for station in stations.station:
        rows = raw[raw.station == station].set_index("timestamp").reindex(required)
        if rows[[*POLLUTANTS, *WEATHER_VARS]].isna().any().any():
            raise RuntimeError(f"Incomplete hourly coverage for {station}")
    cams_now = raw[raw["timestamp"] == now][["station", "pm25", "pm10"]]

    token = os.getenv("WAQI_TOKEN")
    ground = None
    if token:
        try:
            ground = fetch_ground_stations(token)
        except Exception as e:
            logger.warning("Ground station fetch failed, using model data only: %s", e)
    calib = calibrate(stations, cams_now, ground)
    matched = int(calib["ground_station"].notna().sum())

    if matched:
        source, detail = "live", f"CPCB ground stations via WAQI ({matched} matched) + CAMS"
    else:
        source, detail = "model-only", "CAMS atmospheric model (no ground calibration)"
    return assemble_snapshot(raw, stations, now, calib, source, detail, matched)


def build_offline_snapshot():
    """Snapshot from the bundled Dec 2024 sample, extended with persistence for the recursion."""
    res = _load_resources()
    stations = res["stations"]
    raw = res["sample"][RAW_COLUMNS].copy()
    now = raw["timestamp"].max()

    future = []
    last = raw[raw["timestamp"] == now]
    for h in range(1, HORIZON_HOURS - MODEL_LEAD_HOURS + 1):
        f = last.copy()
        f["timestamp"] = now + pd.Timedelta(hours=h)
        future.append(f)
    raw = pd.concat([raw, *future], ignore_index=True)

    calib = calibrate(stations, last[["station", "pm25", "pm10"]], None)
    return assemble_snapshot(
        raw, stations, now, calib, "offline-sample",
        "Bundled sample data from Dec 2024 (live sources unreachable)", 0,
    )


# ── Snapshot cache + background refresh ─────────────────────────────────────

_snapshot = None
_version = 0
_lock = threading.Lock()
_first_live_done = threading.Event()
_refresh_thread = None
_refresh_status = {
    "last_attempt": None,
    "last_success": None,
    "last_error": None,
    "consecutive_failures": 0,
}


def _set_snapshot(snap):
    global _snapshot, _version
    with _lock:
        _snapshot = snap
        _version += 1


def _load_persisted():
    snap = read_pickle(SNAPSHOT_PATH)
    # Old live data is preferable to an unrelated historical demo; freshness
    # remains based on its original timestamp, even after a process restart.
    if isinstance(snap, dict) and snap.get("source") in ("live", "model-only"):
        return snap
    return None


def refresh_live():
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    # The lock plus timestamp check avoids each Gunicorn worker polling APIs.
    with FileLock(SNAPSHOT_PATH + ".lock", timeout=180):
        persisted = _load_persisted()
        if persisted:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(persisted["generated_at"])).total_seconds()
            if 0 <= age < REFRESH_SECONDS:
                _set_snapshot(persisted)
                with _lock:
                    _refresh_status.update(last_success=persisted["generated_at"], last_error=None, consecutive_failures=0)
                _first_live_done.set()
                return True
        return _refresh_live_unlocked()


def _refresh_live_unlocked():
    attempted = datetime.now(timezone.utc).isoformat()
    try:
        snap = build_live_snapshot()
        _set_snapshot(snap)
        with _lock:
            _refresh_status.update(
                last_attempt=attempted, last_success=attempted, last_error=None, consecutive_failures=0,
            )
        try:
            atomic_pickle(SNAPSHOT_PATH, snap)
        except OSError as e:
            logger.warning("Could not persist snapshot: %s", e)
        logger.info("Live snapshot refreshed (%s)", snap["source"])
        return True
    except Exception as e:
        logger.warning("Live refresh failed: %s", e)
        # Keep serving the previous snapshot; freshness() reports how old it is
        with _lock:
            _refresh_status["last_attempt"] = attempted
            _refresh_status["last_error"] = f"{type(e).__name__}: {e}"[:300]
            _refresh_status["consecutive_failures"] += 1
        return False
    finally:
        _first_live_done.set()


def _refresh_loop():
    while True:
        try:
            refresh_live()
        except Exception as exc:
            # Lock/storage failures must not permanently kill the refresh thread.
            logger.warning("Refresh coordination failed: %s", type(exc).__name__)
            _first_live_done.set()
        failures = _refresh_status["consecutive_failures"]
        time.sleep(min(REFRESH_SECONDS * 2 ** min(failures, 3), 6 * 3600))


def start_background_refresh():
    """Start the periodic live refresh (no-op when ATMOS_LIVE=0)."""
    global _refresh_thread
    if not LIVE_ENABLED or _refresh_thread is not None:
        _first_live_done.set()
        return
    persisted = _load_persisted()
    if persisted:
        _set_snapshot(persisted)
    _refresh_thread = threading.Thread(target=_refresh_loop, name="atmos-refresh", daemon=True)
    _refresh_thread.start()


def get_snapshot():
    """Current snapshot; waits briefly for the first live attempt before falling back."""
    global _snapshot, _version
    if _snapshot is None and LIVE_ENABLED and _refresh_thread is not None:
        _first_live_done.wait(FIRST_LIVE_WAIT_SECONDS)
    with _lock:
        if _snapshot is None:
            _snapshot = build_offline_snapshot()
            _version += 1
        return _snapshot


def freshness(snap, now=None):
    """How current a snapshot's data is, computed at read time.

    status is "sample" for the bundled offline data, otherwise "current" or
    "stale" depending on the age of the observations it was built from.
    """
    now = now or datetime.now(timezone.utc)
    observed = datetime.fromisoformat(snap["observed_at"])
    ground_times = [w.get("ground_observed_at") for w in snap.get("wards", []) if w.get("ground_observed_at")]
    if ground_times:
        observed = min(observed, *(datetime.fromisoformat(t) for t in ground_times))
    age_minutes = max(0, int((now - observed).total_seconds() // 60))
    if snap["source"] == "offline-sample":
        status = "sample"
    elif age_minutes > STALE_AFTER_MINUTES:
        status = "stale"
    else:
        status = "current"
    with _lock:
        refresh = dict(_refresh_status)
    return {
        "status": status,
        "data_timestamp": observed.isoformat(),
        "data_age_minutes": age_minutes,
        "stale_after_minutes": STALE_AFTER_MINUTES,
        "last_successful_refresh": refresh["last_success"],
        "last_refresh_error": refresh["last_error"],
        "consecutive_refresh_failures": refresh["consecutive_failures"],
    }


def snapshot_version():
    get_snapshot()
    return _version
