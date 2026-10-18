# Atmos — AI-Powered Urban Air Quality Intelligence

An air quality forecasting and intervention platform built for Delhi. Predicts ward-level pollution 72 hours ahead, explains what's causing it, and generates actionable enforcement tickets for city officials. Built for the ET AI Hackathon 2026, Problem Statement 5.

**One-liner:** *Atmos turns air quality from a passive reading into an actionable plan: predict, explain, intervene.*

## Architecture

- **Frontend:** Next.js 16 (App Router), React, Leaflet (maps), Recharts (charts), Vanilla CSS
- **Backend:** FastAPI (Python 3.13), Uvicorn
- **ML Engine:** Optuna-tuned LightGBM (quantile regression: q10/q50/q90), SHAP TreeExplainer for attribution
- **Chatbot:** Google Gemini 2.5 Flash with RAG (live data injected into prompts), bilingual EN/Hindi
- **Data Sources:** Open-Meteo Air Quality API (CAMS satellite model), CPCB ground stations via WAQI (calibration), Sentinel-2 NDVI via Google Earth Engine, OpenStreetMap Overpass API (hospitals/schools)

## Setup Instructions

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:
```
GEMINI_API_KEY=your_gemini_api_key_here
# Optional, defaults to gemini-2.5-flash
GEMINI_MODEL=gemini-2.5-flash
# Deployed frontend URL(s), comma-separated. Local/LAN dev servers on any port are always allowed.
ALLOWED_ORIGINS=https://your-frontend.example.com
# Free token from https://aqicn.org/data-platform/token/ - enables CPCB ground-station calibration
WAQI_TOKEN=your_waqi_token_here
# Optional: minutes between live refreshes (default 30); set ATMOS_LIVE=0 to stay on the bundled sample
ATMOS_REFRESH_MINUTES=30
```

### Live data

The backend refreshes a forecast snapshot in the background (every 30 min by default), so API requests are served from memory in milliseconds:

1. **Model inputs:** hourly pollutants (Open-Meteo / CAMS) for each station plus weather. These are the same sources the model was trained on.
2. **Prediction:** the LightGBM quantile models predict PM2.5 24h ahead from each of the last 24 hourly feature rows (+1 to +24h), then recursively out to +72h using their own median predictions as lag inputs, with the 10th and 90th percentiles giving the uncertainty band.
3. **Ground calibration:** CAMS underestimates Delhi PM2.5 and is too coarse to tell neighbouring stations apart, so each station is scaled to its CPCB monitor reading via WAQI; stations without a monitor nearby get an inverse-distance-weighted ratio. Without `WAQI_TOKEN` the forecasts are uncalibrated (`data_source: "model-only"`).

The server needs outbound access to `air-quality-api.open-meteo.com`, `api.open-meteo.com` and `api.waqi.info`. If they are unreachable, it falls back to the bundled Dec 2024 sample and every response reports `data_source: "offline-sample"`, which the UI shows as a banner.

### Retraining the model

The bundled models were trained on only 12 days of data (19–31 Dec 2024), so they have never seen other seasons. To retrain on the full 2023–2024 history (needs access to Open-Meteo, including `archive-api.open-meteo.com`):

```bash
cd backend
./retrain.sh
```

> Training pairs UTC-labelled pollutant data with IST-labelled weather (a 5.5h offset). Live inference reproduces this so predictions stay consistent; fixing it means changing `fetch_weather.py` to UTC and retraining.

Start the server:
```bash
uvicorn main:app --reload
```
API runs at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend
npm install
```

Optionally create `.env.local` in `frontend/`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the dev server:
```bash
npm run dev
```
App runs at `http://localhost:3000`.

## Testing

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

All 67 tests cover happy paths, boundary conditions, integration flows, latency SLAs (<500ms per endpoint), and the live pipeline (with Open-Meteo/WAQI responses stubbed). Tests always run offline (`ATMOS_LIVE=0`).

## Features

- **72h Ward-Level Forecast** — LightGBM quantile models (q10/q50/q90) predict PM2.5 for every hour of the next 72h: direct 24h-ahead predictions for +1 to +24h, then recursive steps to +72h, calibrated to CPCB ground readings
- **SHAP Pollution Attribution** — TreeExplainer computes per-ward feature contributions, grouped into four categories (Traffic & Time, Weather, Historical/Baseline, Geography & Infra)
- **Enforcement Tickets** — Auto-generated tickets for the worst wards, with real population counts, school/hospital counts from OSM data, and ML-simulated AQI reduction percentages
- **What-If Simulator** — Zeroes out relevant pollutant features (NO2/CO for traffic, PM10 for construction, SO2 for industrial) and re-runs the model to compute counterfactual AQI reduction
- **Vulnerability Overlay** — Maps schools, hospitals, and elderly care centers (fetched from OpenStreetMap) against pollution hotspots
- **Atmos Assistant** — Gemini-powered RAG chatbot that injects live forecast data, blame scores, and enforcement tickets into the prompt. Supports English and Hindi queries
- **Prediction Map** — Inverse-distance-weighted interpolation fills all 290 wards from the 29 stations; a timeline lets you play or scrub the forecast from now to +72h across the city
- **Historical Data** — Measured hourly PM2.5, PM10, NO₂, SO₂, CO and O₃ for the last 30 days, city-wide or per ward

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/forecast/{city}` | City overview with all ward forecasts |
| GET | `/api/forecast/{city}/timeline` | Hourly predicted AQI for every ward (drives the map timeline) |
| GET | `/api/forecast/{city}/{ward_id}` | Detailed 72h forecast for one ward |
| GET | `/api/history/{city}` | Measured hourly pollutant history (`?ward_id=`, `?hours=`) |
| GET | `/api/blame/{city}/{ward_id}` | SHAP attribution breakdown |
| GET | `/api/enforce/{city}` | Auto-generated enforcement tickets |
| GET | `/api/vulnerable/{city}` | Schools, hospitals, elderly care centers |
| POST | `/api/whatif` | What-If intervention simulator |
| POST | `/api/chat` | Gemini RAG chatbot |
| GET | `/api/health` | Health check |

## Project Structure

```
atmos/
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── routers/                 # API route handlers
│   ├── models/                  # ML models, forecaster, schemas
│   ├── services/                # Live data pipeline, chatbot
│   ├── data/                    # Data ingestion & preprocessing
│   ├── data_store/              # Trained models, cached data, GeoJSON
│   ├── tests/                   # 67 pytest tests
│   ├── retrain.sh               # Rebuild training data and retrain
│   └── train_models.py          # Optuna hyperparameter tuning pipeline
├── frontend/
│   ├── app/                     # Next.js pages (forecast, blame, enforce)
│   ├── components/              # Map, sidebar, topbar
│   ├── lib/                     # API client, AQI scale + spatial helpers
│   └── public/                  # Static assets, GeoJSON
└── docs/                        # API contract, project docs
```
