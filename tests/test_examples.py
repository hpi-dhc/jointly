"""
This file contains test functions for the examples in the documentation.

Do not modify the examples from the documentation.
Run these tests with the working directory set to the repository root.
"""


def test_main_readme_example():
    import tempfile
    import traceback

    from jointly.helpers_plotting import plot_reference_columns
    import jointly
    from jointly import ShakeExtractor
    from jointly.helpers import calculate_magnitude
    import pandas as pd

    # load source dataframes with datetime index
    faros_df = pd.read_csv(
        "./test-data/faros-plus-physilog/faros.csv.gz", index_col=[0], parse_dates=True
    )
    physilog_df = pd.read_csv(
        "./test-data/faros-plus-physilog/physilog.csv.gz",
        index_col=[0],
        parse_dates=True,
    )

    # the magnitude is a common property that keeps shake information but removes axis relevance
    faros_df["Accel Mag"] = calculate_magnitude(
        faros_df, ["Accel X", "Accel Y", "Accel Z"]
    )
    physilog_df["Accel Mag"] = calculate_magnitude(
        physilog_df, ["Accel X", "Accel Y", "Accel Z"]
    )

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
    extractor = ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=15)
    extractor.end_window_length = pd.Timedelta(seconds=10)
    extractor.min_length = 3
    extractor.threshold = 0.55

    # prepare the synchronizer
    synchronizer = jointly.Synchronizer(
        sources, reference_source_name="Faros", extractor=extractor
    )

    # get_synced_data returns a dictionary of sensor names to synced DataFrames
    # if the extractor parameters are wrong, print the problem and show the data
    try:
        synchronizer.get_synced_data()
    except Exception:
        traceback.print_exc()
        plot_reference_columns(sources)

    # save a file for each input sensor somewhere
    with tempfile.TemporaryDirectory() as tmp_dir:
        synchronizer.save_pickles(tmp_dir)
