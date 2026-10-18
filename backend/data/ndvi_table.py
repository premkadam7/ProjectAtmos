"""The ward NDVI table shared by data/fetch_ndvi.py (writer) and data/preprocess.py (reader).

Contract: CSV at NDVI_PATH with columns Ward_Name (as in delhi_wards.geojson)
and ndvi_mean (mean Sentinel-2 NDVI over the ward polygon, -1..1). Wards
whose NDVI could not be computed are left empty (NaN), never written as 0.

Ward names are not unique in the boundary file (two distinct wards are both
"RAM NAGAR"), so a name may repeat only as often as it does there; readers
must treat such names as ambiguous (see ambiguous_ward_names). One boundary
polygon has neither a name nor a number; it cannot be keyed, so unnamed rows
are dropped.
"""
import os

import pandas as pd

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NDVI_PATH = os.path.join(BACKEND_DIR, "data_store", "cache", "delhi_wards_ndvi.csv")
NDVI_COLUMNS = ["Ward_Name", "ndvi_mean"]
MIN_COVERAGE = 0.9   # share of wards that must have a value before a new table replaces the old one


class NdviSchemaError(ValueError):
    pass


def validate_ndvi_table(df: pd.DataFrame, expected_wards=None) -> pd.DataFrame:
    missing = [c for c in NDVI_COLUMNS if c not in df.columns]
    if missing:
        raise NdviSchemaError(f"NDVI table is missing columns {missing}; expected {NDVI_COLUMNS}, got {list(df.columns)}")
    df = df[df["Ward_Name"].notna() & (df["Ward_Name"].astype(str).str.strip() != "")]
    if expected_wards is not None:
        expected_wards = [w for w in expected_wards if w]
    counts = df["Ward_Name"].value_counts()
    if expected_wards is not None:
        allowed = pd.Series(list(expected_wards)).value_counts()
        too_many = [n for n, c in counts.items() if c > allowed.get(n, 0) and n in allowed]
        if too_many:
            raise NdviSchemaError(f"NDVI table repeats wards more often than the boundary file: {too_many[:5]}")
    values = pd.to_numeric(df["ndvi_mean"], errors="coerce")
    if ((values < -1) | (values > 1)).any():
        raise NdviSchemaError("ndvi_mean values must be within -1..1")
    if expected_wards is not None:
        unknown = set(df["Ward_Name"]) - set(expected_wards)
        if unknown:
            raise NdviSchemaError(f"NDVI table names wards not in the boundary file: {sorted(unknown)[:5]}")
    return df[NDVI_COLUMNS].assign(ndvi_mean=values)


def ambiguous_ward_names(df: pd.DataFrame) -> list:
    """Names that identify more than one ward and so cannot be joined by name."""
    counts = df["Ward_Name"].value_counts()
    return sorted(counts[counts > 1].index)


def load_ndvi_table(path: str = None) -> pd.DataFrame:
    return validate_ndvi_table(pd.read_csv(path or NDVI_PATH))


def write_ndvi_table(rows: list, expected_wards, path: str = None) -> pd.DataFrame:
    """Validate and atomically replace the NDVI table.

    rows: dicts with Ward_Name and ndvi_mean (None/NaN where computation failed).
    Refuses to replace the table if too few wards have values.
    """
    path = path or NDVI_PATH
    df = validate_ndvi_table(pd.DataFrame(rows, columns=NDVI_COLUMNS), expected_wards)
    named = [w for w in expected_wards if w]
    coverage = df["ndvi_mean"].notna().sum() / max(len(named), 1)
    if coverage < MIN_COVERAGE:
        raise NdviSchemaError(
            f"Only {coverage:.0%} of wards have NDVI values (minimum {MIN_COVERAGE:.0%}); keeping the existing table"
        )
    tmp = f"{path}.tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)
    return df
