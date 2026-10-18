from datetime import datetime, timezone, timedelta
import pandas as pd
import pytest
from services import input_cache as cache
from services import live_pipeline as lp


def frame(value=1):
    now = pd.Timestamp.now(tz='UTC').tz_localize(None).floor('h')
    return pd.DataFrame({'timestamp': pd.date_range(now-pd.Timedelta(days=3), periods=120, freq='h'), 'pm25': value})


def test_incremental_refresh_reuses_and_replaces_overlapping_inputs(tmp_path, monkeypatch):
    path = tmp_path/'input.pkl'
    calls=[]
    def fetch(days):
        calls.append(days)
        return frame(len(calls))
    first=cache.incremental_frame(path, fetch, ['timestamp'])
    assert cache.incremental_frame(path, fetch, ['timestamp']).equals(first)
    assert calls == [3]
    saved=cache.read_pickle(path)
    saved['fetched_at'] -= 3700
    cache.atomic_pickle(path,saved)
    updated=cache.incremental_frame(path, fetch, ['timestamp'])
    assert calls == [3,1]
    assert not updated.timestamp.duplicated().any()
    assert (updated.pm25 == 2).all()


def test_failed_input_refresh_does_not_advance_cache(tmp_path):
    path=tmp_path/'input.pkl'
    cache.incremental_frame(path,lambda days: frame(),['timestamp'])
    before=path.read_bytes()
    def fail(days):
        raise RuntimeError('provider down')
    with pytest.raises(RuntimeError):
        cache.incremental_frame(path,fail,['timestamp'],ttl_seconds=0)
    assert path.read_bytes() == before


def test_429_honours_retry_after_without_repeated_requests(tmp_path,monkeypatch):
    calls=[]
    class Response:
        status_code=429
        headers={'Retry-After':'3600'}
    def fetch(*args,**kwargs):
        calls.append(1)
        return Response()
    monkeypatch.setattr(cache.requests,'get',fetch)
    for _ in range(2):
        with pytest.raises(RuntimeError,match='rate limited'):
            cache.request_json('https://api.open-meteo.com/v1/forecast',{},tmp_path)
    assert len(calls)==1


def test_old_live_snapshot_survives_restart(tmp_path,monkeypatch):
    path=tmp_path/'snapshot.pkl'
    monkeypatch.setattr(lp,'SNAPSHOT_PATH',str(path))
    old=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
    saved={'source':'live','generated_at':old,'observed_at':old}
    cache.atomic_pickle(path,saved)
    assert lp._load_persisted()==saved
    assert lp.freshness(saved)['status']=='stale'


def test_shared_recent_snapshot_skips_provider_calls(tmp_path,monkeypatch):
    path=tmp_path/'snapshot.pkl'
    monkeypatch.setattr(lp,'RUNTIME_DIR',str(tmp_path))
    monkeypatch.setattr(lp,'SNAPSHOT_PATH',str(path))
    monkeypatch.setattr(lp,'_snapshot',None)
    now=datetime.now(timezone.utc).isoformat()
    cache.atomic_pickle(path,{'source':'model-only','generated_at':now,'observed_at':now})
    def fail():
        pytest.fail('worker duplicated a refresh')
    monkeypatch.setattr(lp,'build_live_snapshot',fail)
    assert lp.refresh_live()


def test_ground_timestamp_drives_staleness():
    now=datetime.now(timezone.utc)
    snap={'source':'live','observed_at':now.isoformat(),
          'wards':[{'ground_observed_at':(now-timedelta(hours=3)).isoformat()}]}
    assert lp.freshness(snap,now)['status']=='stale'
