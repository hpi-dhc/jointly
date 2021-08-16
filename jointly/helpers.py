"""Contains plotting helpers"""
import logging
from pprint import pprint
from typing import List, Tuple, Iterable

import numpy as np
import pandas as pd

from jointly import ShakeMissingException
from jointly.types import SyncPairs, SynchronizationPair, SyncPairTimeshift

logger = logging.getLogger("jointly.helpers")


def calculate_magnitude(
    df: pd.DataFrame, of_cols: List[str], title: str = "Magnitude"
) -> pd.DataFrame:
    """Calculate the magnitude of a subset of columns from a DataFrame"""
    data = df[of_cols]
    result = np.sqrt(np.square(data).sum(axis=1))
    result.name = title
    return result.to_frame(name=title)


def normalize(x: List[float]):
    """Normalizes signal to interval [-1, 1] with mean 0."""
    if len(x) <= 1:
        raise ValueError("Cannot normalize list with less than 2 entries")
    x_centered = x - np.mean(x)
    x_maximum = np.max(np.abs(x_centered))
    if x_maximum == 0:
        raise ZeroDivisionError("input vector is all-zero")
    x_normalized = x_centered / x_maximum
    return x_normalized


def get_equidistant_signals(signals: pd.DataFrame, frequency: float):
    """
    Returns dataframe with columns from ``signals`` sampled equidistantly at the specified frequency.

    :param signals: the columns of this dataframe will be independently resampled
    :param frequency: the target frequency in Hz
    :return: equidistantly sampled dataframe
    """
    freq = "{}N".format(int(1e9 / frequency))
    df = pd.DataFrame(
        {col: signals[col].dropna().resample(freq).nearest() for col in signals.columns}
    )
    index = pd.date_range(
        start=pd.to_datetime(df.index.min(), unit="s"),
        end=pd.to_datetime(df.index.max(), unit="s"),
        freq=freq,
    )
    return df.set_index(index)


def get_max_ref_frequency(signals: pd.DataFrame) -> float:
    """
    Get the maximum frequency in the dataframe

    :param signals: input dataframe with the given signals
    :return: float describing the maximum frequency in the source data.
    """
    if not isinstance(signals, pd.DataFrame):
        raise ValueError("Can only find the max frequency of DataFrames")
    if len(signals.columns) == 0:
        raise ValueError("Can't get the max frequency of 0 columns")

    frequencies = signals.aggregate(infer_freq)
    return np.amax(frequencies)


def infer_freq(series: pd.Series) -> float:
    """
    Infer the frequency of a series by finding the median temporal distance between its elements.

    :param series: the frequency of this series will be inferred
    :return: frequency, as a float, measured in Hz
    """
    index = series.dropna().index
    time_deltas = index[1:] - index[:-1]
    median = np.median(time_deltas)
    return np.timedelta64(1, "s") / median


def stretch_signals(
    source: pd.DataFrame, factor: float, start_time: pd.DatetimeIndex
) -> pd.DataFrame:
    """
    Returns a copy of DataFrame with stretched DateTimeIndex.

    :param source: the index of this DataFrame will be stretched.
    :param factor: the factor by which to streth the DateTimeIndex
    :param start_time: first index, i.e., time, in the dataframe
    :return: copy of the dataframe with stretched index
    """
    timedelta = source.index - start_time
    new_index = timedelta * factor + start_time
    df = source.set_index(new_index, verify_integrity=True)
    return df


def get_stretch_factor(
    segments: SynchronizationPair, timeshifts: SyncPairTimeshift
) -> float:
    """
    Get the stretch factor required to stretch the duration between segments such that it will fit exactly to the
    signal when shifted by the amount given by timeshifts.

    :param segments: the segment instance containing the segment info to be stretched
    :param timeshifts: the timeshifts that should be applied to make the signal align to the reference signal
    :return: a float as described above
    """
    old_length = segments["second"]["start"] - segments["first"]["start"]
    new_length = old_length + timeshifts["second"] - timeshifts["first"]
    stretch_factor = new_length / old_length
    return stretch_factor


def verify_segments(signals: Iterable[str], segments: SyncPairs):
    """Verify that two synchronization points (i.e., start and end) have been found for each signal."""
    for signal in signals:
        for segment in ["first", "second"]:
            for part in ["start", "end"]:
                try:
                    segments[signal][segment][part]
                except KeyError:
                    print("Dumping all detected segments:")
                    pprint(segments)
                    raise ShakeMissingException(
                        f"No {segment} shake detected for {signal}, missing the {part}"
                    )


def get_segment_data(
    dataframe: pd.DataFrame, segments: SyncPairs, col: str, segment: str
) -> Tuple[pd.Timestamp, pd.Timestamp, pd.DataFrame]:
    start = segments[col][segment]["start"]
    end = segments[col][segment]["end"]
    return start, end, dataframe[col][start:end]
