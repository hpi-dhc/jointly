import pandas as pd
import pytest

from jointly import ShakeExtractor, Synchronizer, BadWindowException
from tests.parquet_reader import get_parquet_test_data


def test_window_params():
    e = ShakeExtractor()
    with pytest.raises(ValueError):
        e.start_window_length = 3
    with pytest.raises(ValueError):
        e.end_window_length = 3

    e.start_window_length = pd.Timedelta(seconds=3)
    e.end_window_length = pd.Timedelta(seconds=3)


def test_threshold_param():
    e = ShakeExtractor()
    with pytest.raises(ValueError):
        e.threshold = 3
    with pytest.raises(ValueError):
        e.threshold = -1
    with pytest.raises(ValueError):
        e.threshold = 0
    with pytest.raises(ValueError):
        e.threshold = 1
    e.threshold = 0.5


def test_window_length_error():
    base_data = get_parquet_test_data("test-data.parquet")
    reference_signal, target_signal = "A", "B"
    sources = {
        reference_signal: {"data": base_data.copy(), "ref_column": "ACCELERATION_Z"},
        target_signal: {"data": base_data, "ref_column": "ACCELERATION_Z"},
    }
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=50)
    extractor.end_window_length = pd.Timedelta(seconds=3)
    extractor.min_length = 3
    extractor.threshold = 0.5

    with pytest.raises(BadWindowException):
        Synchronizer(sources, reference_signal, extractor).get_sync_params()
