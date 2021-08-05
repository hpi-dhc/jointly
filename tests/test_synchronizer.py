"""Happy path tests for the synchronizer and shake extractor"""
import os.path
import tempfile

import pandas as pd
import pytest

import jointly
from jointly import ShakeExtractor
from jointly.helpers import stretch_signals
from tests.parquet_reader import get_parquet_test_data


def test_happy_path_faros_internal():
    ref_data = get_parquet_test_data("faros-internal.parquet", 666)
    target_data = get_parquet_test_data("faros-internal.parquet", 667)
    reference_signal, target_signal = "Internal", "Faros"
    sources = {
        reference_signal: {"data": ref_data, "ref_column": "ACCELERATION_Z"},
        target_signal: {"data": target_data, "ref_column": "ACCELERATION_Z"},
    }
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=17)
    extractor.end_window_length = pd.Timedelta(seconds=10)
    extractor.min_length = 3
    extractor.threshold = 0.19

    synchronizer = jointly.Synchronizer(sources, reference_signal, extractor)
    sync_result = synchronizer.get_sync_params()

    assert (
        sync_result[reference_signal]["timeshift"] is None
    ), "Should not have timeshift for reference signal"
    assert (
        sync_result[reference_signal]["stretch_factor"] == 1
    ), "Should not stretch reference signal"

    assert sync_result[target_signal]["timeshift"] == pd.Timedelta(
        "-1 days +23:59:59.070000"
    ), "Should have timeshift of 0 for equal signal"
    assert (
        sync_result[target_signal]["stretch_factor"] == 1.0506424792139077
    ), "Should have stretching factor of 1 for equal signal"


def test_happy_path_equal_data():
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
    sync_result = synchronizer.get_sync_params()

    assert (
        sync_result[reference_signal]["timeshift"] is None
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


def test_happy_path_shifted_data():
    base_data = get_parquet_test_data("test-data.parquet")
    reference_signal, target_signal = "A", "B"
    target_df = base_data.shift(-22, freq="100ms")

    sources = {
        reference_signal: {"data": base_data.copy(), "ref_column": "ACCELERATION_Z"},
        target_signal: {"data": target_df, "ref_column": "ACCELERATION_Z"},
    }
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=5)
    extractor.end_window_length = pd.Timedelta(seconds=3)
    extractor.min_length = 3
    extractor.threshold = 0.5

    synchronizer = jointly.Synchronizer(sources, reference_signal, extractor)
    sync_result = synchronizer.get_sync_params()

    assert (
        sync_result[reference_signal]["timeshift"] is None
    ), "Should not have timeshift for reference signal"
    assert (
        sync_result[reference_signal]["stretch_factor"] == 1
    ), "Should not stretch reference signal"

    assert sync_result[target_signal]["timeshift"] == pd.Timedelta(
        "0 days 00:00:02.197549725"
    ), "Should have timeshift of 0 for equal signal"
    assert (
        sync_result[target_signal]["stretch_factor"] == 1
    ), "Should have stretching factor of 1 for equal signal"


def test_happy_path_shifted_stretched_data():
    base_data = get_parquet_test_data("test-data.parquet")
    reference_signal, target_signal = "A", "B"
    target_df = base_data.shift(-22, freq="100ms")
    target_df = stretch_signals(target_df, 1.1, target_df.index.min())

    sources = {
        reference_signal: {"data": base_data.copy(), "ref_column": "ACCELERATION_Z"},
        target_signal: {"data": target_df, "ref_column": "ACCELERATION_Z"},
    }
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=5)
    extractor.end_window_length = pd.Timedelta(seconds=3)
    extractor.min_length = 3
    extractor.threshold = 0.5

    synchronizer = jointly.Synchronizer(sources, reference_signal, extractor)
    sync_result = synchronizer.get_sync_params()

    assert (
        sync_result[reference_signal]["timeshift"] is None
    ), "Should not have timeshift for reference signal"
    assert (
        sync_result[reference_signal]["stretch_factor"] == 1
    ), "Should not stretch reference signal"

    assert sync_result[target_signal]["timeshift"] == pd.Timedelta(
        "0 days 00:00:02.197549725"
    ), "Should have timeshift of 0 for equal signal"
    assert (
        sync_result[target_signal]["stretch_factor"] == 0.9101123595505618
    ), "Should have stretching factor of 1 for equal signal"


def test_happy_path_save_pickles():
    ref_data = get_parquet_test_data("faros-internal.parquet", 666)
    target_data = get_parquet_test_data("faros-internal.parquet", 667)
    reference_signal, target_signal = "Internal", "Faros"
    sources = {
        reference_signal: {"data": ref_data, "ref_column": "ACCELERATION_Z"},
        target_signal: {"data": target_data, "ref_column": "ACCELERATION_Z"},
    }
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=17)
    extractor.end_window_length = pd.Timedelta(seconds=10)
    extractor.min_length = 3
    extractor.threshold = 0.19

    synchronizer = jointly.Synchronizer(sources, reference_signal, extractor)

    with tempfile.TemporaryDirectory() as tmp_dir:
        synchronizer.save_pickles(tmp_dir)
        synced_data = synchronizer.get_synced_data()

        for signal, signal_df in synced_data.items():
            pickle_path = os.path.join(tmp_dir, f"{signal.upper()}.PICKLE")
            assert os.path.isfile(pickle_path)
            assert pd.read_pickle(pickle_path).equals(signal_df)


def test_bad_table_spec_save_tables():
    ref_data = get_parquet_test_data("faros-internal.parquet", 666)
    target_data = get_parquet_test_data("faros-internal.parquet", 667)
    reference_signal, target_signal = "Internal", "Faros"
    sources = {
        reference_signal: {"data": ref_data, "ref_column": "ACCELERATION_Z"},
        target_signal: {"data": target_data, "ref_column": "ACCELERATION_Z"},
    }
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=17)
    extractor.end_window_length = pd.Timedelta(seconds=10)
    extractor.min_length = 3
    extractor.threshold = 0.19

    synchronizer = jointly.Synchronizer(sources, reference_signal, extractor)

    with tempfile.TemporaryDirectory() as tmp_dir:
        with pytest.raises(ValueError):
            synchronizer.save_data(
                tmp_dir, tables={"N/A": {"Faros": ["N/A"]}}, save_total_table=False
            )
        with pytest.raises(ValueError):
            synchronizer.save_data(
                tmp_dir,
                tables={"N/A": {"N/A": ["ACCELERATION_Y"]}},
                save_total_table=False,
            )


def test_happy_path_save_tables():
    ref_data = get_parquet_test_data("faros-internal.parquet", 666)
    target_data = get_parquet_test_data("faros-internal.parquet", 667)
    reference_signal, target_signal = "Internal", "Faros"
    sources = {
        reference_signal: {"data": ref_data, "ref_column": "ACCELERATION_Z"},
        target_signal: {"data": target_data, "ref_column": "ACCELERATION_Z"},
    }
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=17)
    extractor.end_window_length = pd.Timedelta(seconds=10)
    extractor.min_length = 3
    extractor.threshold = 0.19

    synchronizer = jointly.Synchronizer(sources, reference_signal, extractor)

    acc_columns = ["ACCELERATION_X", "ACCELERATION_Y", "ACCELERATION_Z"]
    with tempfile.TemporaryDirectory() as tmp_dir:
        tables = {
            "ACC": {"Faros": acc_columns, "Internal": acc_columns},
            "ECG": {"Faros": ["ECG"]},
        }
        synchronizer.save_data(tmp_dir, tables=tables, save_total_table=False)
        for file in ["ACC", "ECG", "SYNC"]:
            file_path = os.path.join(tmp_dir, f"{file}.csv")

            assert os.path.isfile(file_path), f"{file_path} should exist"
            df = pd.read_csv(file_path)

            if file == "ACC":
                assert len(df) == 4115, "Should have saved all acc values"
                assert "timestamp" in df.columns, "Should have saved timestamp column"
                for col in acc_columns:
                    for device in tables["ACC"]:
                        assert (
                            f"{device}_{col}" in df.columns
                        ), f"Should have saved {device}_{col}"
            elif file == "ECG":
                assert len(df) == 15100, "Should have saved all ecg values"
                assert "timestamp" in df.columns, "Should have saved timestamp column"
            elif file == "SYNC":
                for source in ["Faros", "Internal"]:
                    assert (
                        source in df.columns
                    ), f"Should have saved {source} in SYNC.csv"
                assert "Unnamed: 0" in df.columns, "Should have saved index column"


def test_happy_path_save_total_table():
    ref_data = get_parquet_test_data("faros-internal.parquet", 666)
    target_data = get_parquet_test_data("faros-internal.parquet", 667)
    reference_signal, target_signal = "Internal", "Faros"
    sources = {
        reference_signal: {"data": ref_data, "ref_column": "ACCELERATION_Z"},
        target_signal: {"data": target_data, "ref_column": "ACCELERATION_Z"},
    }
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=17)
    extractor.end_window_length = pd.Timedelta(seconds=10)
    extractor.min_length = 3
    extractor.threshold = 0.19

    synchronizer = jointly.Synchronizer(sources, reference_signal, extractor)
    with tempfile.TemporaryDirectory() as tmp_dir:
        synchronizer.save_data(tmp_dir, tables=None, save_total_table=True)
        file_path = os.path.join(tmp_dir, "TOTAL.csv")
        assert os.path.isfile(file_path), f"{file_path} should exist"

        df = pd.read_csv(file_path)
        assert len(df.columns) == 21, "Should save all sensors from internal and faros"
        assert len(df) == 18518, "Should create exact number of synced result items"
