"""
This file contains test functions for the examples in the documentation.

Do not modify the examples from the documentation.
"""

import os
import pytest


@pytest.fixture(scope="function")
def change_to_repo_root(request):
    if os.getcwd().endswith("tests"):
        os.chdir("..")
    yield
    os.chdir(request.config.invocation_dir)


def test_usage_logging(change_to_repo_root):
    import logging
    from jointly.log import logger

    logger.setLevel(logging.DEBUG)


def test_save_data(change_to_repo_root):
    import pandas as pd
    import tempfile
    import traceback

    import jointly

    # load source dataframes with datetime index
    faros_df = pd.read_csv(
        "./test-data/faros-plus-physilog/faros.csv.gz", index_col=[0], parse_dates=True
    )
    physilog_df = pd.read_csv(
        "./test-data/faros-plus-physilog/physilog.csv.gz",
        index_col=[0],
        parse_dates=True,
    )

    # the magnitude is a common property that keeps shake information without axis relevance
    faros_df["Accel Mag"] = jointly.calculate_magnitude(
        faros_df, ["Accel X", "Accel Y", "Accel Z"]
    )
    physilog_df["Accel Mag"] = jointly.calculate_magnitude(
        physilog_df, ["Accel X", "Accel Y", "Accel Z"]
    )

    # create dictionary of source sensors
    sources = {
        "Faros": {
            "data": faros_df,
            "ref_column": "Accel Mag",
        },
        "Physilog": {
            "data": physilog_df,
            "ref_column": "Accel Mag",
        },
    }

    # set shake extraction parameters
    extractor = jointly.ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=15)
    extractor.end_window_length = pd.Timedelta(seconds=10)
    extractor.min_length = 3
    extractor.threshold = 0.55

    # prepare the synchronizer
    synchronizer = jointly.Synchronizer(
        sources, reference_source_name="Faros", extractor=extractor
    )

    # define output format for two files, one containing all acceleration
    # data, the other the ECG data
    tables = {
        "ACC": {
            "Faros": ["Accel X", "Accel Y", "Accel Z"],
            "Physilog": ["Accel X", "Accel Y", "Accel Z"],
        },
        "ECG": {
            "Faros": ["ECG"],
        },
    }

    # if the extractor parameters are wrong, print the problem and show the data
    try:
        # get_synced_data returns a dictionary of sensor names to synced DataFrames
        with tempfile.TemporaryDirectory() as tmp_dir:
            synchronizer.save_data(tmp_dir, tables=tables, save_total_table=False)
            print("test")
    except Exception:
        traceback.print_exc()
        jointly.plot_reference_columns(sources)


def test_usage_df_head(change_to_repo_root):
    import pandas as pd

    faros_df = pd.read_csv(
        "./test-data/faros-plus-physilog/faros.csv.gz", index_col=[0], parse_dates=True
    )
    print(faros_df.head())


def test_usage_extractor_params(change_to_repo_root):
    import pandas as pd
    import jointly

    extractor = jointly.ShakeExtractor()

    # The start window should be long enough to contain
    # only the start shake in every data stream
    extractor.start_window_length = pd.Timedelta(seconds=15)

    # The end window (measured from the end of data)
    # should be exactly long enough to contain
    # only the end shake in every data stream
    extractor.end_window_length = pd.Timedelta(seconds=3)

    # Set to at most the number of shakes you did
    extractor.min_length = 3

    # Shakes are only accepted if they are higher than the
    # threshold (with all data normalized).
    extractor.threshold = 0.5


def test_main_readme_example(change_to_repo_root):
    import pandas as pd
    import tempfile
    import traceback

    import jointly

    # load source dataframes with datetime index
    faros_df = pd.read_csv(
        "./test-data/faros-plus-physilog/faros.csv.gz", index_col=[0], parse_dates=True
    )
    physilog_df = pd.read_csv(
        "./test-data/faros-plus-physilog/physilog.csv.gz",
        index_col=[0],
        parse_dates=True,
    )

    # the magnitude is a common property that keeps shake information without axis relevance
    faros_df["Accel Mag"] = jointly.calculate_magnitude(
        faros_df, ["Accel X", "Accel Y", "Accel Z"]
    )
    physilog_df["Accel Mag"] = jointly.calculate_magnitude(
        physilog_df, ["Accel X", "Accel Y", "Accel Z"]
    )

    # create dictionary of source sensors
    sources = {
        "Faros": {
            "data": faros_df,
            "ref_column": "Accel Mag",
        },
        "Physilog": {
            "data": physilog_df,
            "ref_column": "Accel Mag",
        },
    }

    # set shake extraction parameters
    extractor = jointly.ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=15)
    extractor.end_window_length = pd.Timedelta(seconds=10)
    extractor.min_length = 3
    extractor.threshold = 0.55

    # prepare the synchronizer
    synchronizer = jointly.Synchronizer(
        sources, reference_source_name="Faros", extractor=extractor
    )

    # if the extractor parameters are wrong, print the problem and show the data
    try:
        # get_synced_data returns a dictionary of sensor names to synced DataFrames
        synchronizer.get_synced_data()
    except Exception:
        traceback.print_exc()
        jointly.plot_reference_columns(sources)

    # save a file for each input sensor somewhere
    with tempfile.TemporaryDirectory() as tmp_dir:
        synchronizer.save_pickles(tmp_dir)
