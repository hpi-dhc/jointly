# -*- coding: utf-8 -*-
"""Tests for `jointly` package."""
import tempfile
import traceback

import numpy as np
import pandas as pd

import jointly
from jointly import ShakeExtractor
from jointly.helpers import plot_reference_columns
from tests.parquet_reader import get_parquet_test_data


def test_happy_path():
    base_data = get_parquet_test_data("test-data.parquet")
    reference_signal, target_signal = "A", "B"
    sources = {
        reference_signal: {"data": base_data.copy(), "ref_column": "ACCELERATION_Z"},
        target_signal: {"data": base_data, "ref_column": "ACCELERATION_Z"},
    }
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=5)
    extractor.end_window_length = pd.Timedelta(seconds=3)
    extractor.min_length = 3
    extractor.threshold = 0.5

    synchronizer = jointly.Synchronizer(sources, reference_signal, extractor)
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            sync_result = synchronizer.save_pickles(tmp_dir)["SYNC"]
        except Exception:
            traceback.print_exc()
            plot_reference_columns(sources)
            assert False, "Should not throw exception"

    assert np.isnan(
        sync_result[reference_signal]["timeshift"]
    ), "Should not have timeshift for reference signal"
    assert (
        sync_result[reference_signal]["stretch_factor"] == 1
    ), "Should not stretch reference signal"

    assert sync_result[target_signal]["timeshift"] == pd.Timedelta(
        seconds=0
    ), "Should have timeshift of 0 for equal signal"
    assert (
        sync_result[target_signal]["stretch_factor"] == 1
    ), "Should have stretching factor of 1 for equal signal"


def test_extract_shakes(get_test_data):
    """Verify that shake extraction works on this example"""
    print("hello")
