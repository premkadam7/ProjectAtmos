# Atmos — AI-Powered Urban Air Quality Intelligence

An air quality forecasting and intervention platform built for Delhi. Predicts ward-level pollution 72 hours ahead, explains what's causing it, and generates actionable enforcement tickets for city officials. Built for the ET AI Hackathon 2026, Problem Statement 5.

**One-liner:** *Atmos turns air quality from a passive reading into an actionable plan: predict, explain, intervene.*

## Architecture

- **Frontend:** Next.js 16 (App Router), React, Leaflet (maps), Recharts (charts), Vanilla CSS
- **Backend:** FastAPI (Python 3.13), Uvicorn
- **ML Engine:** Optuna-tuned LightGBM (quantile regression: q10/q50/q90), SHAP TreeExplainer for attribution
- **Chatbot:** Google Gemini 1.5 Flash with RAG (live data injected into prompts), bilingual EN/Hindi
- **Data Sources:** Open-Meteo Air Quality API (CAMS satellite model), Sentinel-2 NDVI via Google Earth Engine, OpenStreetMap Overpass API (hospitals/schools)

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
```

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

All 60 tests cover happy paths, boundary conditions, integration flows, and latency SLAs (<500ms per endpoint).

## Features

- **72h Ward-Level Forecast** — LightGBM predicts PM2.5 24h ahead (RMSE 29.90, beating naive persistence baseline of 32.27 by 7.4%), then extrapolates to 72h with diurnal correction and uncertainty bands (q10/q90)
- **SHAP Pollution Attribution** — TreeExplainer computes per-ward feature contributions, grouped into four categories (Traffic & Time, Weather, Historical/Baseline, Geography & Infra)
- **Enforcement Tickets** — Auto-generated tickets for the worst wards, with real population counts, school/hospital counts from OSM data, and ML-simulated AQI reduction percentages
- **What-If Simulator** — Zeroes out relevant pollutant features (NO2/CO for traffic, PM10 for construction, SO2 for industrial) and re-runs the model to compute counterfactual AQI reduction
- **Vulnerability Overlay** — Maps schools, hospitals, and elderly care centers (fetched from OpenStreetMap) against pollution hotspots
- **Atmos Assistant** — Gemini-powered RAG chatbot that injects live forecast data, blame scores, and enforcement tickets into the prompt. Supports English and Hindi queries
- **Spatial Interpolation** — Nearest-neighbor interpolation fills 290 GeoJSON wards from 29 monitored stations for a continuous city-wide heatmap

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/forecast/{city}` | City overview with all ward forecasts |
| GET | `/api/forecast/{city}/{ward_id}` | Detailed 72h forecast for one ward |
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
│   ├── services/                # Chatbot service
│   ├── data/                    # Data ingestion & preprocessing
│   ├── data_store/              # Trained models, cached data, GeoJSON
│   ├── tests/                   # 60 pytest tests (4 tiers)
│   └── train_models.py          # Optuna hyperparameter tuning pipeline
├── frontend/
│   ├── app/                     # Next.js pages (forecast, blame, enforce)
│   ├── components/              # Map, sidebar, topbar
│   ├── lib/                     # API client, mock data
│   └── public/                  # Static assets, GeoJSON
└── docs/                        # API contract, project docs
```
