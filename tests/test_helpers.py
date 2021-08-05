import copy

import pandas as pd
import pytest

from jointly import ShakeMissingException
from jointly.helpers import calculate_magnitude, normalize, verify_segments


def test_calculate_magnitude():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [-1.5, 2, 0], "z": [-1.5, 25, 1234]})
    magnitude = calculate_magnitude(df, ["x", "y", "z"], "testname")
    correct = pd.DataFrame(
        {"testname": [2.345207879911715, 25.15949125081825, 1234.0036466720833]}
    )
    assert (magnitude == correct).all().all(), "Should have correct magnitude results"
    df["Magnitude"] = magnitude
    assert (
        df["Magnitude"] == magnitude["testname"]
    ).all(), "Should be possible to set+rename result to old dataframe"


def test_normalize():
    assert ([-1, 0, 1] == normalize([1, 2, 3])).all(), "should be normalized"
    assert ([-1, 0, 1] == normalize([-1, 0, 1])).all(), "should be normalized"

    with pytest.raises(ValueError):
        normalize([])
    with pytest.raises(ValueError):
        normalize([1])
    with pytest.raises(ZeroDivisionError):
        normalize([0, 0])


def test_get_equidistant_signals():
    assert False


def test_get_max_ref_frequency():
    assert False


def test_infer_freq():
    assert False


def test_stretch_signals():
    assert False


def test_get_stretch_factor():
    assert False


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
    assert False
