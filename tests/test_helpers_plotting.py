from unittest.mock import patch

import matplotlib
import pandas as pd
import pytest

from jointly import ShakeExtractor, Synchronizer, get_equidistant_signals
from jointly.helpers_plotting import plot_reference_columns, plot_segments
from tests.parquet_reader import get_parquet_test_data


@patch("jointly.helpers_plotting.plt.show")
def test_plot_segments(mocked_show):
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

    synchronizer = Synchronizer(sources, reference_signal, extractor)
    segments = extractor.get_segments(
        get_equidistant_signals(synchronizer.ref_signals, synchronizer.sampling_freq)
    )

    with pytest.raises(ValueError):
        plot_segments(synchronizer.ref_signals, segments)

    plot_segments(synchronizer.ref_signals, segments, together=True)
    plot_segments(synchronizer.ref_signals, segments, separate=True)


@patch("jointly.helpers_plotting.plt.show")
def test_plot_reference_columns(mocked_show):
    base_data = get_parquet_test_data("test-data.parquet")
    reference_signal, target_signal = "A", "B"
    sources = {
        reference_signal: {"data": base_data.copy(), "ref_column": "ACCELERATION_Z"},
        target_signal: {"data": base_data, "ref_column": "ACCELERATION_Z"},
    }
    plot_reference_columns(sources)
