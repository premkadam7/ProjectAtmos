# Project: Atmos Backend Features Implementation

## Architecture
- FastAPI backend serving Delhi's air quality predictions and SHAP blame analysis.
- Integrates LangChain + Gemini API for RAG conversational chatbot.
- Uses Open-Meteo Air Quality API (CAMS satellite model) for historical pollution data, OpenStreetMap Overpass API for location caching, and Optuna-tuned LightGBM quantile models for forecasting and What-If scenarios.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | E2E Testing Track | Develop E2E tests for R1-R4 (Tiers 1-4) in parallel; publish `TEST_READY.md`. | None | IN_PROGRESS (Conv: 27de77a0-fdd5-46dd-a0df-683a9b65c75f) |
| 2 | R2: Vulnerable Locations | Implement `GET /api/vulnerable/delhi` with Overpass API fetching & GeoJSON caching. | None | IN_PROGRESS (via Conv: 77f13338-5067-4f31-904d-3aecdbc66ec4) |
| 3 | R3: What-If Simulator | Implement `POST /api/whatif` with counterfactual feature manipulation and prediction. | None | IN_PROGRESS (via Conv: 77f13338-5067-4f31-904d-3aecdbc66ec4) |
| 4 | R1: Gemini RAG Chatbot | Implement LangChain + Gemini RAG pipeline and `POST /api/chat` with SSE streaming. | None | IN_PROGRESS (via Conv: 77f13338-5067-4f31-904d-3aecdbc66ec4) |
| 5 | R4: Demo Pre-computation | Pre-compute all forecasts, SHAP blame, tickets, and cache them for instant load. | M2, M3, M4 | IN_PROGRESS (via Conv: 77f13338-5067-4f31-904d-3aecdbc66ec4) |
| 6 | E2E Verification & Audit | Pass 100% of E2E test suite and run white-box adversarial coverage hardening (Tier 5). | M1, M5 | PLANNED |

## Interface Contracts
### Vulnerable Locations API
- Endpoint: `GET /api/vulnerable/{city}`
- Response: Pydantic schema `VulnerableResponse` (containing list of hospital/school/elderly_care)

### What-If Simulator API
- Endpoint: `POST /api/whatif`
- Request: Pydantic schema `WhatIfRequest` (ward_id, intervention, duration_hours)
- Response: Pydantic schema `WhatIfResponse` (current_forecast, with_intervention, reduction, reduction_percentage)

### Chat API
- Endpoint: `POST /api/chat`
- Request: Pydantic schema `ChatRequest` (message, language, conversation_id)
- Response: Pydantic schema `ChatResponse` or SSE stream

## Code Layout
- `backend/main.py` - FastAPI entry point
- `backend/routers/` - FastAPI routers (forecast, blame, enforce, chat, vulnerable, whatif)
- `backend/models/` - Schemas (`schemas.py`) and ML inference/SHAP logic (`forecaster.py`)
- `backend/services/` - Chatbot service (`chatbot.py`)
- `backend/data/` - Preprocessing, ingesting, boundaries utilities
- `backend/tests/` - Integration tests
- `data_store/` - Data cache, models, and GeoJSON files
