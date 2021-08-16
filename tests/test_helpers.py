import copy

import numpy as np
import pandas as pd
import pytest

from jointly import ShakeMissingException, SyncPairTimeshift
from jointly.helpers import (
    calculate_magnitude,
    normalize,
    verify_segments,
    get_segment_data,
    infer_freq,
    get_max_ref_frequency,
    get_stretch_factor,
    stretch_signals,
    get_equidistant_signals,
)
from jointly.types import SynchronizationPair
from tests.parquet_reader import get_parquet_test_data


def test_calculate_magnitude():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [-1.5, 2, 0], "z": [-1.5, 25, 1234]})
    magnitude = calculate_magnitude(df, ["x", "y", "z"], "testname")
    correct = pd.DataFrame(
        {"testname": [2.345207879911715, 25.15949125081825, 1234.0036466720833]}
    )
    assert magnitude.equals(correct), "Should have correct magnitude results"
    df["Magnitude"] = magnitude
    # noinspection PyUnresolvedReferences
    assert df["Magnitude"].equals(
        magnitude["testname"]
    ), "Should be possible to set+rename result to old dataframe"


def test_normalize():
    assert np.array_equal(normalize([1, 2, 3]), [-1, 0, 1]), "should be normalized"
    assert np.array_equal(normalize([-1, 0, 1]), [-1, 0, 1]), "should be normalized"

    with pytest.raises(ValueError):
        normalize([])
    with pytest.raises(ValueError):
        normalize([1])
    with pytest.raises(ZeroDivisionError):
        normalize([0, 0])


def test_get_equidistant_signals():
    test_data = get_parquet_test_data("faros-internal.parquet", 667)

    result = get_equidistant_signals(test_data, frequency=1_000)
    for col in result.columns:
        assert infer_freq(result[col]) == 1000, f"{col} should have 1000 Hz"

    result = get_equidistant_signals(test_data, frequency=500)
    for col in result.columns:
        assert infer_freq(result[col]) == 500, f"{col} should have 500 Hz"

    result = get_equidistant_signals(test_data, frequency=1)
    for col in result.columns:
        assert infer_freq(result[col]) == 1, f"{col} should have 1 Hz"


def test_get_max_ref_frequency():
    test_data = get_parquet_test_data("faros-internal.parquet", 667)

    assert get_max_ref_frequency(test_data) == 500, "max(all) should be 500 Hz"
    assert (
        get_max_ref_frequency(test_data[["ACCELERATION_X", "ACCELERATION_Y"]]) == 100
    ), "max(acc) should be 100 Hz"
    assert (
        get_max_ref_frequency(test_data["ACCELERATION_Y"].to_frame()) == 100
    ), "max(acc) should be 100 Hz"

    with pytest.raises(ValueError):
        get_max_ref_frequency(test_data["ACCELERATION_X"])

    with pytest.raises(ValueError):
        get_max_ref_frequency(pd.DataFrame())


def test_infer_freq():
    test_data = get_parquet_test_data("faros-internal.parquet", 667)

    assert infer_freq(test_data["ECG"]) == 500, "ECG should be 500 Hz"
    assert infer_freq(test_data["ACCELERATION_X"]) == 100, "Acc. should be 100 Hz"
    assert infer_freq(test_data["ACCELERATION_Y"]) == 100, "Acc. should be 100 Hz"
    assert infer_freq(test_data["ACCELERATION_Z"]) == 100, "Acc. should be 100 Hz"


def test_stretch_signals():
    test_idx = pd.date_range(start="1/1/2018", periods=8)
    test_data = [42] * 8
    test_df = pd.DataFrame(test_data, test_idx)

    result = stretch_signals(test_df, factor=1, start_time=test_idx.min())
    assert result is not test_df, "must be a copy"
    assert result.equals(test_df), "must be equal"

    result = stretch_signals(test_df, factor=2, start_time=test_idx.min())
    assert result is not test_df, "must be a copy"
    assert result.index.max() == pd.to_datetime(
        "1/15/2018"
    ), "must have double the distance equal"


def test_get_stretch_factor():
    def _ts(seconds: int) -> pd.Timestamp:
        return pd.Timestamp(seconds, unit="s")

    def _td(seconds: int) -> pd.Timedelta:
        return pd.Timedelta(seconds, unit="s")

    segments: SynchronizationPair = {
        "first": {"start": _ts(1), "end": _ts(3)},
        "second": {"start": _ts(11), "end": _ts(14)},
    }

    timeshift: SyncPairTimeshift = {"first": _td(5), "second": _td(0)}
    assert (
        get_stretch_factor(segments, timeshift) == 0.5
    ), "should double the speed if distance halves"

    timeshift: SyncPairTimeshift = {"first": _td(0), "second": _td(10)}
    assert (
        get_stretch_factor(segments, timeshift) == 2
    ), "should halve the speed if distance doubles"


def test_verify_segments():
    """delete all parts of a proper SyncPairs instance and check if the verification alg throws"""
    good_segments = {
        "s": {
            "first": {"start": 0, "end": 0},
            "second": {"start": 0, "end": 0},
        },
        "d": {
            "first": {"start": 0, "end": 0},
            "second": {"start": 0, "end": 0},
        },
    }
    columns = ["s", "d"]
    # noinspection PyTypeChecker
    verify_segments(columns, good_segments)

    with pytest.raises(ShakeMissingException):
        verify_segments(columns, {})

    for signal_name, signal_dict in good_segments.items():
        for segment_name, segment_dict in signal_dict.items():
            for position_name in segment_dict:
                copied = copy.deepcopy(good_segments)
                del copied[signal_name][segment_name][position_name]

                with pytest.raises(ShakeMissingException):
                    # noinspection PyTypeChecker
                    verify_segments(columns, copied)
            copied = copy.deepcopy(good_segments)
            del copied[signal_name][segment_name]

            with pytest.raises(ShakeMissingException):
                # noinspection PyTypeChecker
                verify_segments(columns, copied)
        copied = copy.deepcopy(good_segments)
        del copied[signal_name]

        with pytest.raises(ShakeMissingException):
            # noinspection PyTypeChecker
            verify_segments(columns, copied)


def test_get_segment_data():
    segments = {
        "s": {"first": {"start": 0, "end": 2}},
    }
    df = pd.DataFrame({"s": [1, 2, 3, 4]})
    result_expected = 0, 2, pd.Series([1, 2], name="s")
    # noinspection PyTypeChecker
    result_actual = get_segment_data(df, segments, "s", "first")

    assert len(result_actual) == 3, "should have start, end, data"
    assert result_expected[0] == result_actual[0], "should find right start"
    assert result_expected[1] == result_actual[1], "should find right end"
    assert result_expected[2].equals(result_actual[2]), "should extract correct portion"
