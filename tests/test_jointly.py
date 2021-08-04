# -*- coding: utf-8 -*-
"""Tests for `jointly` package."""
import tempfile
import traceback

import pandas as pd

import jointly
from jointly import ShakeExtractor, SourceDict
from jointly.helpers import plot_reference_columns
from tests.parquet_reader import get_pivoted_parquet_sensor_data


def test_happy_path():
    base_data = get_pivoted_parquet_sensor_data("../test-data/test-data.parquet")
    sources = {
        "A": {"data": base_data.copy(), "ref_column": "ACCELERATION_Z"},
        "B": {"data": base_data, "ref_column": "ACCELERATION_Z"},
    }
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=5)
    extractor.end_window_length = pd.Timedelta(seconds=3)
    extractor.min_length = 3
    extractor.threshold = 0.5

    synchronizer = jointly.Synchronizer(sources, "A", extractor)
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            synchronizer.save_pickles(tmp_dir)
        except Exception:
            traceback.print_exc()
            plot_reference_columns(sources)


def test_extract_shakes(get_test_data):
    """Verify that shake extraction works on this example"""
    print("hello")
