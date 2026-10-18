"""Live pipeline tests with HTTP responses stubbed in the Open-Meteo / WAQI formats."""
from datetime import datetime, timezone

import pandas as pd
import pytest

from services import live_pipeline as lp


def _now():
    return pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None).floor("h")


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture
def fake_http(monkeypatch):
    """Serve the bundled sample, shifted so it covers now-250h .. now+49h."""
    res = lp._load_resources()
    sample = res["sample"].sort_values(["station", "timestamp"])
    stations = res["stations"]
    now = _now()
    offset = now + pd.Timedelta(hours=49) - sample["timestamp"].max()

    # Two fresh ground readings and one stale one that must be ignored
    anand = stations[stations.station == "Anand Vihar"].iloc[0]
    lodhi = stations[stations.station == "Lodhi Road"].iloc[0]
    fresh = datetime.now(timezone.utc).isoformat()
    feeds = {
        1: {"iaqi": {"pm25": {"v": 350}, "pm10": {"v": 300}}, "city": {"geo": [anand.lat, anand.lon], "name": "Anand Vihar"}, "time": {"iso": fresh}},
        2: {"iaqi": {"pm25": {"v": 120}}, "city": {"geo": [lodhi.lat + 0.005, lodhi.lon], "name": "Lodhi Road"}, "time": {"iso": fresh}},
        3: {"iaqi": {"pm25": {"v": 40}}, "city": {"geo": [28.70, 77.10], "name": "Stale"}, "time": {"iso": "2020-01-01T00:00:00+05:30"}},
    }

    def fake_get(url, params=None, timeout=None):
        if url == lp.AQ_URL:
            out = []
            for st in stations.itertuples():
                s = sample[sample.station == st.station]
                hourly = {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in s["timestamp"] + offset]}
                for src, dst in lp.AQ_VARS.items():
                    hourly[src] = s[dst].tolist()
                out.append({"hourly": hourly})
            return _Resp(out)
        if url == lp.WEATHER_URL:
            s = sample[sample.station == stations.station.iloc[0]]
            hourly = {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in s["timestamp"] + offset]}
            for v in lp.WEATHER_VARS:
                hourly[v] = s[v].tolist()
            return _Resp(hourly and {"hourly": hourly})
        if url.endswith("/map/bounds"):
            return _Resp({"status": "ok", "data": [{"uid": uid} for uid in feeds]})
        uid = int(url.rstrip("/").split("@")[-1])
        return _Resp({"status": "ok", "data": feeds[uid]})

    monkeypatch.setattr(lp.requests, "get", fake_get)
    monkeypatch.setenv("WAQI_TOKEN", "test-token")
    return now


def test_epa_inversion():
    assert lp._epa_aqi_to_concentration(50, lp._EPA_PM25) == pytest.approx(12.0)
    assert lp._epa_aqi_to_concentration(151, lp._EPA_PM25) == pytest.approx(55.5)
    assert lp._epa_aqi_to_concentration(None, lp._EPA_PM25) is None


def test_live_snapshot_calibrates_to_ground(fake_http):
    snap = lp.build_live_snapshot()
    assert snap["source"] == "live"
    assert snap["ground_stations"] == 2

    wards = {w["ward_name"]: w for w in snap["wards"]}
    expected = lp._epa_aqi_to_concentration(350, lp._EPA_PM25)
    assert wards["Anand Vihar"]["current_pm25"] == pytest.approx(expected, rel=0.01)
    assert wards["Anand Vihar"]["ground_station"] == "Anand Vihar"
    assert wards["Lodhi Road"]["current_pm25"] < wards["Anand Vihar"]["current_pm25"]

    # Unmatched stations are interpolated, so wards no longer collapse to a few values
    assert len({w["current_aqi"] for w in snap["wards"]}) > 10


def test_live_forecast_shape(fake_http):
    snap = lp.build_live_snapshot()
    now = fake_http
    for w in snap["wards"]:
        hourly = w["hourly"]
        assert len(hourly) == lp.HORIZON_HOURS
        assert pd.Timestamp(hourly[0]["timestamp"]).tz_localize(None) == now + pd.Timedelta(hours=1)
        for h in hourly:
            assert h["aqi_low"] <= h["aqi"] <= h["aqi_high"]
            assert h["pm10"] is not None
        # The first hour is anchored to the current observation
        assert hourly[0]["pm25"] == pytest.approx(w["current_pm25"], rel=0.2)


def test_live_history_is_observed_only(fake_http):
    snap = lp.build_live_snapshot()
    hist = snap["history"]
    assert hist["timestamp"].max() == fake_http
    assert set(lp.POLLUTANTS) <= set(hist.columns)


def test_falls_back_to_model_only_without_token(fake_http, monkeypatch):
    monkeypatch.delenv("WAQI_TOKEN")
    snap = lp.build_live_snapshot()
    assert snap["source"] == "model-only"
    assert all(w["calibration_ratio"] == 1.0 for w in snap["wards"])


def test_history_endpoint(client):
    resp = client.get("/api/history/delhi?hours=48")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_source"] == "offline-sample"
    assert 0 < len(data["series"]) <= 48
    assert {"aqi", "pm25", "pm10", "co", "no2", "so2", "o3"} <= set(data["series"][0])


def test_timeline_endpoint(client):
    resp = client.get("/api/forecast/delhi/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["timestamps"]) == lp.HORIZON_HOURS
    assert all(len(v) == lp.HORIZON_HOURS for v in data["wards"].values())


# ── Freshness (F08) ──────────────────────────────────────────────────────────

def _live_snapshot_observed(hours_ago):
    snap = dict(lp.build_offline_snapshot())
    observed = datetime.now(timezone.utc) - pd.Timedelta(hours=hours_ago)
    snap.update(source="live", observed_at=observed.isoformat(), generated_at=observed.isoformat())
    return snap


def test_freshness_current_then_stale():
    assert lp.freshness(_live_snapshot_observed(0.5))["status"] == "current"
    old = lp.freshness(_live_snapshot_observed(5))
    assert old["status"] == "stale"
    assert old["data_age_minutes"] >= 5 * 60 - 1


def test_offline_sample_is_never_reported_current():
    assert lp.freshness(lp.build_offline_snapshot())["status"] == "sample"


def test_repeated_refresh_failure_keeps_data_but_reports_stale(monkeypatch):
    snap = _live_snapshot_observed(5)
    monkeypatch.setattr(lp, "_snapshot", snap)
    monkeypatch.setattr(lp, "_refresh_status", dict(lp._refresh_status, consecutive_failures=0, last_error=None))

    def boom():
        raise ConnectionError("upstream down")
    monkeypatch.setattr(lp, "build_live_snapshot", boom)

    for _ in range(3):
        assert lp.refresh_live() is False

    current = lp.get_snapshot()
    assert current is snap
    assert current["observed_at"] == snap["observed_at"]   # not silently advanced
    f = lp.freshness(current)
    assert f["status"] == "stale"
    assert f["consecutive_refresh_failures"] == 3
    assert "upstream down" in f["last_refresh_error"]


def test_api_reports_freshness(client):
    data = client.get("/api/forecast/delhi").json()
    assert data["freshness"]["status"] == "sample"
