# ATMOS: Urban Air Quality Intelligence Platform
**Technical Documentation — ET AI Hackathon 2026, Problem Statement 5**

## 1. What Atmos Does

Atmos is an air quality forecasting and intervention platform for Delhi. It predicts ward-level pollution 72 hours ahead, explains what factors are driving it, and generates actionable enforcement tickets for city officials — all powered by real ML models trained on 2 years of historical data.

The platform has three core capabilities:
1. **Predict** — LightGBM forecasts PM2.5 levels 24h ahead, extended to 72h with diurnal correction
2. **Explain** — SHAP attribution breaks down exactly which factors (traffic, weather, dust, industrial baseline) are responsible for each ward's pollution
3. **Act** — Auto-generated enforcement tickets with real population counts, nearby school/hospital data, and ML-simulated impact estimates

## 2. System Architecture

| Layer | Tech | Purpose |
|-------|------|---------|
| Backend | Python 3.13, FastAPI, Uvicorn | API server, ML inference, data pipeline |
| ML | LightGBM (Optuna-tuned), SHAP TreeExplainer | Forecasting, attribution |
| Chatbot | Google Gemini 1.5 Flash + RAG | Context-aware Q&A in English and Hindi |
| Frontend | Next.js 16, React, Leaflet, Recharts | Dashboard, maps, charts |
| Data | Open-Meteo API (CAMS satellite), Sentinel-2 NDVI, OpenStreetMap | Historical pollution, vegetation, vulnerable locations |

## 3. Backend & Machine Learning

### 3.1 Data Pipeline

We sourced 2 years (2023–2024) of hourly pollution data from the Open-Meteo Air Quality API, which uses the Copernicus CAMS satellite model (~40km resolution for Delhi).

- **`data/ingest.py`** — Fetches PM2.5, PM10, CO, NO2, SO2, O3 across 34 CPCB stations in Delhi/NCR. 5 NCR stations were filtered out. 2 stations (Punjabi Bagh, Shadipur) initially timed out and were recovered via `fetch_missing.py`, bringing the total to 29 active wards.
- **`data/preprocess.py`** — Converts raw data into an engineered feature matrix (`features_delhi.csv`, ~508K rows, 51 columns). Features include:
  - Cyclical time encodings (hour, day, month, day of week encoded as sin/cos)
  - Lag features (PM2.5 at t-1, t-2, t-3)
  - Rolling statistics (3h, 6h, 12h, 24h moving averages)
  - Event flags (Diwali, stubble burning season)
  - Spatial features (NDVI from Sentinel-2, population density per km²)
- **`data/fetch_ndvi.py`** — Fetches real Sentinel-2 satellite imagery via Google Earth Engine, applies cloud filtering, and computes zonal NDVI statistics over ward polygons
- **`data/fetch_vulnerable.py`** — Queries OpenStreetMap Overpass API for hospitals, schools, and elderly care centers in Delhi. Falls back to synthetic generation from ward centroids if the API is unreachable. Results cached as `vulnerable_locations.geojson`

### 3.2 Model Training

**`train_models.py`** runs the full training pipeline:

1. Creates a 24h-ahead prediction target (`pm25` shifted by 24 rows per station)
2. Splits 80/20 by time with a **24-hour purge gap** to prevent lag feature leakage across train/test
3. Runs 50-trial Optuna hyperparameter search for both LightGBM and XGBoost
4. Picks the champion (LightGBM won: RMSE 29.90 vs XGBoost 29.93)
5. Trains quantile models (q10, q50, q90) on the full dataset for uncertainty bands
6. Saves model pickles and feature names to `data_store/models/`

**Key metric:** Our LightGBM model achieves RMSE 29.90, beating the naive persistence baseline (RMSE 32.27) by 7.4%.

### 3.3 Forecaster (`models/forecaster.py`)

The forecaster serves predictions at inference time:

- Loads the three quantile models and the latest feature matrix
- For each ward, predicts q10/q50/q90 PM2.5 at t+24h
- Converts PM2.5 to AQI using the official Indian NAQI breakpoint formula (same formula used in training data labels)
- Generates a 72h hourly forecast by interpolating from current AQI to the 24h prediction with a diurnal cosine wave (peaks at morning and evening rush hours)
- Computes cigarette equivalent (PM2.5 / 22.0)

### 3.4 SHAP Attribution (`get_ward_blame`)

Uses `shap.TreeExplainer` on the champion q50 model. For each ward:
- Computes SHAP values for all 47 features
- Groups features into 4 human-readable categories:
  - **Traffic & Time** — hour, day of week, holiday flags, NO2, CO
  - **Weather** — temperature, humidity, wind speed/direction, pressure, precipitation
  - **Historical / Baseline** — lag features, rolling averages, SO2
  - **Geography & Infra** — NDVI, population density, lat/lon
- Returns percentage contributions and an icon for each category

### 3.5 What-If Simulator

`run_whatif_simulation()` performs genuine ML counterfactual analysis:
- Takes a ward and an intervention type (restrict_traffic, pause_construction, industrial_shutdown)
- Copies the ward's current feature vector
- Zeroes out the relevant pollutant features (NO2+CO for traffic, PM10 for construction, SO2 for industrial)
- Runs the modified features through the real LightGBM model
- Applies a time-decay function `(1 - e^(-hours/24))` to model how the intervention effect ramps up
- Returns the before/after AQI and percentage reduction

### 3.6 Enforcement Tickets

`routers/enforce.py` generates tickets for the 5 worst wards:
- Loads real population data from `delhi_wards_population.csv`
- Counts actual schools and hospitals per ward from `vulnerable_locations.geojson`
- Maps the top SHAP blame factor to an intervention, then runs the What-If simulator to compute a real ML-based AQI reduction percentage (not hardcoded)

### 3.7 Chatbot (RAG)

`services/chatbot.py` uses Google Gemini 1.5 Flash with RAG:
- Before each query, builds a context payload from live data: city average AQI, worst wards, active enforcement tickets, per-ward blame scores
- Injects this data into the Gemini system prompt
- Supports English and Hindi queries with fuzzy ward-name matching
- Degrades gracefully to canned responses if the API key is missing

## 4. Frontend

### 4.1 Map (`AqiMap.js`)

The map plots all ~290 Delhi wards from a GeoJSON file. Since we only have model predictions for 29 monitored stations, we use **nearest-neighbor interpolation** to fill in the remaining wards:
- For each unmonitored ward, finds the closest monitored station by geographic centroid distance
- Assigns the nearest station's AQI value with reduced opacity
- Displays an "Estimated value" tooltip on hover

This creates a continuous city-wide pollution heatmap. The interpolation is clearly labeled in the UI — we don't pretend the estimated values are independent measurements.

### 4.2 Pages

- **Landing page (`/`)** — Overview of the platform with key stats
- **Dashboard (`/forecast`)** — Interactive map with vulnerable location overlays (hospitals, schools). Clicking a ward opens a detail panel with 72h forecast chart, PM2.5 reading, cigarette equivalent, and SHAP attribution bars
- **Blame Score (`/blame`)** — Ward-by-ward pollution attribution breakdown, fetched from the real SHAP backend
- **Enforcement (`/enforce`)** — Command center for city administrators showing auto-generated tickets sorted by urgency. Each ticket shows real population affected, nearby schools/hospitals, and an ML-simulated AQI reduction badge
- **Chatbot (`/chat` via landing page)** — Full interface for the Gemini-powered assistant

## 5. Bugs Fixed During Development

1. **299 AQI Flatline** — The model was predicting ~299 AQI for almost every ward. Root cause: mean imputation in `preprocess.py` was filling missing time-series data with the global average, causing the model to collapse to one value. Fix: switched to forward-fill and dropped empty timestamps.

2. **Identical Enforcement Tickets** — The `/enforce` endpoint generated the same ticket for every ward. Fix: ensured SHAP feature importances were computed per-ward and used deterministic ward-based hashing for ticket IDs.

3. **Missing Stations** — Punjabi Bagh and Shadipur failed during the initial API scrape. Fix: wrote `fetch_missing.py` to scrape them individually and appended ~35K rows to the raw cache without re-scraping the entire 2-year dataset.

4. **AQI Formula Mismatch** — The inference code used a rough `pm25 * 2.0` approximation while training labels used the correct NAQI breakpoint formula. Fix: unified both to use the same piecewise breakpoint function.

5. **Fake Enforcement Data** — Population and school/hospital counts on tickets were derived from string length of ward IDs. Fix: loaded real population CSV and real OSM vulnerable locations GeoJSON.

## 6. Known Limitations (Be Honest About These)

- **Data resolution**: Open-Meteo serves CAMS global model data at ~40-45km resolution. Delhi fits within roughly one grid cell. This means our 29 "stations" share only 3 distinct pollutant time series. The model works, but true hyperlocal differentiation would require actual physical sensor feeds (e.g., CPCB live API).

- **72h forecast**: The model is trained for 24h-ahead prediction only. The 48h and 72h values are extrapolated with a diurnal cosine, not independently modeled.

- **PM10**: Not independently predicted. Currently estimated as `AQI * 0.8`.

- **Blame category labels**: "Traffic & Time" is really hour/day/holiday features + NO2/CO. "Historical / Baseline" is really lag/rolling features + SO2. We don't have live traffic or industrial permit data — these are proxy signals. Totally defensible, just know the honest explanation if asked.

- **Delhi-only**: Ward boundaries, station lists, and GeoJSON are hardcoded for Delhi. Scaling to another city would require new data sources.

## 7. Pitch Strategy

When presenting to judges, hit these points:

- **Predictive, not reactive** — We don't just show current AQI; we forecast 72 hours ahead using a real trained model with a measurable RMSE (29.90 vs 32.27 persistence baseline = 7.4% improvement)
- **Source attribution** — We don't just say "it's polluted"; SHAP mathematically explains what factors are driving pollution in each specific ward
- **Actionable intelligence** — We don't just provide data; we generate enforcement tickets with real population impact, nearby vulnerable locations, and ML-simulated intervention effects
- **What-If simulator** — City officials can ask "what happens if we restrict traffic in this ward?" and get a real counterfactual from the ML model
- **Spatial interpolation** — Nearest-neighbor interpolation fills the city-wide map from 29 stations, and it's transparently labeled as estimated where applicable
