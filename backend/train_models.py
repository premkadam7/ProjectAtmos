import pandas as pd
import numpy as np
import os
import joblib
import optuna
import lightgbm as lgb
import xgboost as xgb
from sklearn.metrics import root_mean_squared_error

TARGET = "pm25"

def load_and_split_data():
    path = os.path.join("data_store", "cache", "features_delhi.csv")
    df = pd.read_csv(path)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp").reset_index(drop=True)

    df["target_24h"] = df.groupby("station")[TARGET].shift(-24)
    df = df.dropna(subset=["target_24h"]).reset_index(drop=True)

    features = [c for c in df.columns if c not in ["timestamp", "station", "ward_id", "target_24h", "aqi"]]

    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    train_end_time = train_df['timestamp'].max()
    purge_end_time = train_end_time + pd.Timedelta(hours=24)
    test_df = df[df['timestamp'] > purge_end_time]

    X_train, y_train = train_df[features], train_df["target_24h"]
    X_test, y_test = test_df[features], test_df["target_24h"]

    return X_train, y_train, X_test, y_test, features, df

def objective_lgb(trial, X_train, y_train, X_test, y_test):
    params = {
        "objective": "regression",
        "metric": "rmse",
        "verbosity": -1,
        "boosting_type": "gbdt",
        "n_estimators": trial.suggest_int("n_estimators", 50, 200),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 20, 100),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.6, 1.0),
    }
    model = lgb.LGBMRegressor(**params, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    return root_mean_squared_error(y_test, model.predict(X_test))

def objective_xgb(trial, X_train, y_train, X_test, y_test):
    params = {
        "objective": "reg:squarederror",
        "n_estimators": trial.suggest_int("n_estimators", 50, 200),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
    }
    model = xgb.XGBRegressor(**params, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    return root_mean_squared_error(y_test, model.predict(X_test))

def run_pipeline():
    X_train, y_train, X_test, y_test, features, full_df = load_and_split_data()

    study_lgb = optuna.create_study(direction="minimize")
    study_lgb.optimize(lambda t: objective_lgb(t, X_train, y_train, X_test, y_test), n_trials=50)

    study_xgb = optuna.create_study(direction="minimize")
    study_xgb.optimize(lambda t: objective_xgb(t, X_train, y_train, X_test, y_test), n_trials=50)

    best_lgb = study_lgb.best_value
    best_xgb = study_xgb.best_value

    print(f"LightGBM RMSE: {best_lgb:.2f}")
    print(f"XGBoost RMSE:  {best_xgb:.2f}")

    champion = "LightGBM" if best_lgb < best_xgb else "XGBoost"
    print(f"Champion: {champion}")

    X_full = full_df[features]
    y_full = full_df["target_24h"]

    out_dir = os.path.join("data_store", "models")
    os.makedirs(out_dir, exist_ok=True)

    if champion == "LightGBM":
        params = study_lgb.best_params
        for q in [0.1, 0.5, 0.9]:
            model = lgb.LGBMRegressor(**params, objective="quantile", alpha=q, random_state=42, n_jobs=-1)
            model.fit(X_full, y_full)
            joblib.dump(model, os.path.join(out_dir, f"champion_q{int(q*100)}.pkl"))
    else:
        params = study_xgb.best_params
        for q in [0.1, 0.5, 0.9]:
            model = xgb.XGBRegressor(**params, objective="reg:quantileerror", quantile_alpha=q, random_state=42, n_jobs=-1)
            model.fit(X_full, y_full)
            joblib.dump(model, os.path.join(out_dir, f"champion_q{int(q*100)}.pkl"))

    joblib.dump(features, os.path.join(out_dir, "feature_names.pkl"))
    print("Done.")

if __name__ == "__main__":
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    run_pipeline()
