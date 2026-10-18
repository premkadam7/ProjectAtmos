"""Disk-backed incremental inputs. Locks coordinate workers on a shared disk."""
import json
import os
import pickle
import time
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import requests
from filelock import FileLock


def atomic_pickle(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(f'.{os.getpid()}.tmp')
    with temp.open('wb') as stream:
        pickle.dump(value, stream)
    os.replace(temp, path)


def read_pickle(path):
    try:
        with open(path, 'rb') as stream:
            return pickle.load(stream)
    except (OSError, ValueError, EOFError, pickle.UnpicklingError):
        return None


def request_json(url, params, cache_dir):
    """Respect Retry-After across workers; avoid retry storms on shared hosts."""
    host = requests.utils.urlparse(url).netloc
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    cooldown = root / f'{host}.cooldown.json'
    with FileLock(str(cooldown) + '.lock', timeout=35):
        try:
            until = json.loads(cooldown.read_text())['until']
        except (OSError, ValueError, KeyError):
            until = 0
        if until > time.time():
            raise RuntimeError(f'{host}: rate limited; next attempt after {int(until)} UTC epoch seconds')
        for attempt in range(3):
            try:
                response = requests.get(url, params=params, timeout=30)
                if getattr(response, 'status_code', 200) == 429:
                    retry = response.headers.get('Retry-After', '1800')
                    try:
                        delay = float(retry)
                    except ValueError:
                        try:
                            delay = parsedate_to_datetime(retry).timestamp() - time.time()
                        except (TypeError, ValueError):
                            delay = 1800
                    cooldown.write_text(json.dumps({'until': time.time() + max(60, delay)}))
                    raise RuntimeError(f'{host}: HTTP 429 rate limited; refresh deferred')
                response.raise_for_status()
                return response.json()
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
                status = getattr(getattr(exc, 'response', None), 'status_code', 0)
                if attempt == 2 or (status and status < 500):
                    # Do not put provider URLs (potentially containing API keys) in status.
                    raise RuntimeError(f'{host}: request failed ({status or type(exc).__name__})') from None
                time.sleep(2 ** attempt)


def incremental_frame(path, fetch, keys, ttl_seconds=3600):
    """Bootstrap three days (model needs 48h); subsequently overlap one day.

    Retain a month as history accumulates. Never reuse an expired fetch as a
    successful new observation: failures leave the previous snapshot in place.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + '.lock', timeout=120):
        cached = read_pickle(path)
        now = time.time()
        if cached and 0 <= now - cached['fetched_at'] < ttl_seconds:
            return cached['frame'].copy()
        age_days = (now - cached['fetched_at']) / 86400 if cached else 999
        past_days = 1 if age_days < 1 else 3
        fresh = fetch(past_days)
        if fresh.empty or fresh.isna().any().any():
            raise RuntimeError('Provider returned missing hourly inputs')
        # Forecasts from older requests must not silently become historical data.
        if cached and age_days < 1:
            old = cached['frame']
            fresh = pd.concat([old[old.timestamp < fresh.timestamp.min()], fresh], ignore_index=True)
        fresh = fresh.drop_duplicates(keys, keep='last').sort_values(keys)
        cutoff = pd.Timestamp.now(tz='UTC').tz_localize(None) - pd.Timedelta(days=31)
        fresh = fresh[fresh.timestamp >= cutoff].reset_index(drop=True)
        atomic_pickle(path, {'fetched_at': now, 'frame': fresh})
        return fresh.copy()
