"""The NDVI fetcher's output must be consumable by preprocessing as-is (F18)."""
import json

import pandas as pd
import pytest

from data import ndvi_table
from data.preprocess import merge_ndvi

WARD_NAMES = [f["properties"]["Ward_Name"]
              for f in json.load(open(ndvi_table.BACKEND_DIR + "/data_store/geojson/delhi_wards.geojson"))["features"]]


def _rows(overrides=None, failed=()):
    rows = [{"Ward_Name": n, "ndvi_mean": 0.3} for n in WARD_NAMES]
    for r in rows:
        if r["Ward_Name"] in (overrides or {}):
            r["ndvi_mean"] = overrides[r["Ward_Name"]]
        if r["Ward_Name"] in failed:
            r["ndvi_mean"] = None
    return rows


def test_writer_output_feeds_preprocessing(tmp_path):
    path = tmp_path / "ndvi.csv"
    ndvi_table.write_ndvi_table(_rows({"NARELA": 0.777}), WARD_NAMES, str(path))

    stations = pd.DataFrame({"station": ["Narela", "Rohini"], "ward_id": ["narela", "rohini"]})
    merged = merge_ndvi(stations, str(path))
    assert merged.loc[merged.station == "Narela", "ndvi_mean"].item() == pytest.approx(0.777)
    assert merged.loc[merged.station == "Rohini", "ndvi_mean"].item() == pytest.approx(0.3)
    assert len(merged) == 2   # no duplicated rows


def test_bundled_table_meets_contract():
    df = ndvi_table.load_ndvi_table()
    ndvi_table.validate_ndvi_table(df, WARD_NAMES)


def test_old_fetcher_format_fails_clearly(tmp_path):
    path = tmp_path / "ward_ndvi.csv"
    pd.DataFrame({"ward_id": ["CANT_1"], "ndvi": [0.4]}).to_csv(path, index=False)
    with pytest.raises(ndvi_table.NdviSchemaError, match="missing columns"):
        merge_ndvi(pd.DataFrame({"ward_id": ["x"]}), str(path))


def test_failed_wards_stay_empty_not_zero(tmp_path):
    path = tmp_path / "ndvi.csv"
    ndvi_table.write_ndvi_table(_rows(failed={"NARELA"}), WARD_NAMES, str(path))
    assert pd.read_csv(path).set_index("Ward_Name").loc["NARELA", "ndvi_mean"] != 0
    assert pd.isna(pd.read_csv(path).set_index("Ward_Name").loc["NARELA", "ndvi_mean"])


def test_low_coverage_keeps_existing_table(tmp_path):
    path = tmp_path / "ndvi.csv"
    path.write_text("Ward_Name,ndvi_mean\nNARELA,0.5\n")
    with pytest.raises(ndvi_table.NdviSchemaError, match="keeping the existing table"):
        ndvi_table.write_ndvi_table(_rows(failed=set(WARD_NAMES[:100])), WARD_NAMES, str(path))
    assert path.read_text() == "Ward_Name,ndvi_mean\nNARELA,0.5\n"


def test_ambiguous_ward_names_do_not_duplicate_rows(tmp_path):
    path = tmp_path / "ndvi.csv"
    ndvi_table.write_ndvi_table(_rows(), WARD_NAMES, str(path))
    merged = merge_ndvi(pd.DataFrame({"ward_id": ["ram_nagar"]}), str(path))
    assert len(merged) == 1
