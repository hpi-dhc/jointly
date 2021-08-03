# -*- coding: utf-8 -*-
"""Tests for `jointly` package."""

import random
import pandas as pd
import pytest


@pytest.fixture
def get_test_data():
    """Get test data in the format required by jointly"""

    def _read_csv(path: str) -> pd.DataFrame:
        return pd.read_csv(
            path, sep=";", index_col=0, parse_dates=True, infer_datetime_format=True
        )

    return {
        "Faros": {
            "data": _read_csv("../test-data/sensor1.csv.gz"),
            "ref_column": "acc_mag",
        },
        "Empatica": {
            "data": _read_csv("../test-data/sensor2.csv.gz"),
            "ref_column": "acc_mag",
        },
    }


def test_extract_shakes(get_test_data):
    """Verify that shake extraction works on this example"""
    print("hello")


# def test_max_number_bad(generate_numbers):
#     """Sample test function that fails. Uncomment to see."""
#
#     our_result = jointly.max_number(generate_numbers)
#     assert our_result == max(generate_numbers) + 1
