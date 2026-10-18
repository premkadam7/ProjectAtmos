#!/usr/bin/env bash
# Rebuild the training data from Open-Meteo (2023-2024, all stations) and retrain
# the LightGBM quantile models. Run from anywhere; needs network access to
# air-quality-api.open-meteo.com and archive-api.open-meteo.com.
set -euo pipefail
cd "$(dirname "$0")"

python data/ingest.py         # hourly pollutants per station -> data_store/cache/aqi_delhi.csv
python data/fetch_weather.py  # hourly weather -> data_store/cache/weather_delhi.csv
python data/preprocess.py     # features -> data_store/cache/features_delhi.csv
python train_models.py        # models -> data_store/models/
