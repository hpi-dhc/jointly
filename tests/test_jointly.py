# -*- coding: utf-8 -*-
"""Tests for `jointly` package."""
import os.path
import random
import pandas as pd
import pytest

from tests.parquet_reader import read_parquet_sensor_data, pivot_parquet_sensor_data

_sensor_data_type_group_map = {
    "ACCELERATION_X": "ACCELERATION",
    "ACCELERATION_Y": "ACCELERATION",
    "ACCELERATION_Z": "ACCELERATION",
    "ORIENTATION_X": "ORIENTATION",
    "ORIENTATION_Y": "ORIENTATION",
    "ORIENTATION_Z": "ORIENTATION",
    "LINEAR_ACCELERATION_X": "LINEAR_ACCELERATION",
    "LINEAR_ACCELERATION_Y": "LINEAR_ACCELERATION",
    "LINEAR_ACCELERATION_Z": "LINEAR_ACCELERATION",
    "MAGNETOMETER_X": "MAGNETOMETER",
    "MAGNETOMETER_Y": "MAGNETOMETER",
    "MAGNETOMETER_Z": "MAGNETOMETER",
    "GRAVITY_X": "GRAVITY",
    "GRAVITY_Y": "GRAVITY",
    "GRAVITY_Z": "GRAVITY",
    "LIGHT": "LIGHT",
}


@pytest.fixture
def get_test_data():
    """Get test data in the format required by jointly"""
    base_data = pivot_parquet_sensor_data(
        read_parquet_sensor_data("../test-data/test-data.parquet")
    )

    return {
        "Faros": {
            "data": base_data,
            "ref_column": "acc_mag",
        },
        "Empatica": {
            "data": base_data,
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
