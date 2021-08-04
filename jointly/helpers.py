"""Contains signal processing and plotting helpers"""
import logging
from pprint import pprint
from typing import List, Optional, Tuple

import matplotlib.cm
import numpy as np
import pandas as pd
from matplotlib import pyplot, pyplot as plt
from scipy.signal import correlate

from jointly import ShakeMissingException
from jointly.types import SyncPairs, SourceDict, SyncPairTimeshift

logger = logging.getLogger("jointly.helpers")


def normalize(x: List[float]):
    """Normalizes signal to interval [-1, 1] with mean 0."""
    xn = x - np.mean(x)
    xn = xn / np.max(np.abs(xn))
    return xn


def get_equidistant_signals(signals: pd.DataFrame, frequency: float):
    """
    Returns copy of dataframe with signals
    sampled equidistantly at the specified frequency.
    """
    freq = "{}N".format(int(1e9 / frequency))
    df = pd.DataFrame(
        {col: signals[col].dropna().resample(freq).nearest() for col in signals.columns}
    )
    index = pd.date_range(
        start=pd.to_datetime(signals.index.min(), unit="s"),
        end=pd.to_datetime(signals.index.max(), unit="s"),
        freq=freq,
    )
    return df.set_index(index)


def get_max_ref_frequency(signals: pd.DataFrame) -> float:
    """
    Get the maximum frequency in the dataframe

    :param signals: input dataframe with the given signals
    :return: float describing the maximum frequency in the source data.
    """
    frequencies = signals.aggregate(infer_freq)
    return np.amax(frequencies)


def infer_freq(series: pd.Series) -> float:
    """
    Infer the frequency of a series by finding the median temporal distance between its elements.

    :param series: the frequency of this series will be inferred
    :return: frequency, as a float, measured in Hz
    """
    index = series.dropna().index
    timedeltas = index[1:] - index[:-1]
    median = np.median(timedeltas)
    return np.timedelta64(1, "s") / median


def stretch_signals(
    source: pd.DataFrame, factor: float, start_time=None
) -> pd.DataFrame:
    """
    Returns a copy of DataFrame with stretched DateTimeIndex.

    :param source: the index of this DataFrame will be stretched.
    :param factor: the factor by which to streth the DateTimeIndex
    :param start_time: first index, i.e., time, in the dataframe. Will be calculated if not given.
    :return: copy of the dataframe with stretched index
    """
    df = source.copy()
    if start_time is None:
        start_time = df.index.min()
    logger.debug("Use start time: {}".format(start_time))
    timedelta = df.index - start_time
    new_index = timedelta * factor + start_time
    df.set_index(new_index, inplace=True, verify_integrity=True)
    return df


def get_stretch_factor(segments, timeshifts):
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


def verify_segments(
    columns: Tuple[str, str], segments: SyncPairs, segment_names: List[str]
):
    """Verify that two synchronization points (i.e., start and end) have been found for each signal."""
    for col in columns:
        for segment in segment_names:
            for part in ["start", "end"]:
                try:
                    segments[col][segment][part]
                except KeyError:
                    print("Dumping all detected segments:")
                    pprint(segments)
                    raise ShakeMissingException(
                        f"No {segment} shake detected for {col}, missing the {part}"
                    )


def get_segment_data(
    dataframe: pd.DataFrame, segments: SyncPairs, col: str, segment: str
) -> Tuple[pd.Timestamp, pd.Timestamp, pd.DataFrame]:
    start = segments[col][segment]["start"]
    end = segments[col][segment]["end"]
    return start, end, dataframe[col][start:end]


def get_timeshift_pair(
    dataframe: pd.DataFrame, ref_col: str, sig_col: str, segments: SyncPairs
) -> SyncPairTimeshift:
    """
    Returns timeshifts to synchronize sig_col to ref_col.
    Expects equidistant sampled signals.

    :param dataframe: reference signal dataframe
    :param ref_col: name of the reference signal in segments
    :param sig_col: name of the target signal in segments
    :param segments: all detected synchronization pairs
    :return: timeshift to align the first and second synchronization point
             for the target signal to the reference signal
    """
    timeshifts = {}
    segment_names = ["first", "second"]

    verify_segments((ref_col, sig_col), segments, segment_names)

    fig, axes = None, None
    if logger.isEnabledFor(logging.INFO):
        fig, axes = pyplot.subplots(1, 2, figsize=(15, 4))

    for index, segment in enumerate(segment_names):
        logger.debug(
            f"Calculate timeshift of {segment} segment " f"for {sig_col} to {ref_col}."
        )

        # reference signal segment data extraction
        ref_start, ref_end, ref_data = get_segment_data(
            dataframe, segments, ref_col, segment
        )
        sig_start, sig_end, sig_data = get_segment_data(
            dataframe, segments, sig_col, segment
        )

        # calculate cross-correlation of segments
        cross_corr = correlate(ref_data, sig_data)
        shift_in_samples = np.argmax(cross_corr) - len(sig_data) + 1

        # get timestamp at which sig_segment must start to sync signals
        max_corr_ts = dataframe.index[
            dataframe.index.get_loc(ref_start, method="nearest") + shift_in_samples
        ]
        logger.debug(
            f"Highest correlation with start at "
            f"{max_corr_ts} with {np.max(cross_corr)}."
        )

        # calculate timeshift to move signal to maximize correlation
        timeshifts[segment] = max_corr_ts - sig_start
        logger.debug("Timeshift is {}.".format(str(timeshifts[segment])))

        # plot shifted segments
        if logger.isEnabledFor(logging.INFO):
            try:
                df = dataframe.copy()
                df[sig_col] = df[sig_col].shift(1, freq=timeshifts[segment])
                if axes is not None:
                    axes[index].set_title(
                        f"{segment} segment of {ref_col} and {sig_col}"
                    )
                    df[[ref_col, sig_col]][ref_start:ref_end].plot(ax=axes[index])
            except MemoryError:
                logger.warn(
                    "Couldn't allocate enough memory to plot shifted segments, skipping"
                )

    if logger.isEnabledFor(logging.INFO):
        try:
            if fig is not None:
                fig.tight_layout()
        except MemoryError:
            logger.warn(
                "Couldn't allocate enough memory to plot shifted segments, skipping"
            )

    return timeshifts


def plot_signals(
    df: pd.DataFrame,
    cols: Optional[List[str]] = None,
    title: str = None,
    tags: List[float] = None,
):
    """
    Plot a number of signals.

    :param df: dataframe to plot from
    :param cols: the columns to plot
    :param title: plot title
    :param tags: positions given in float seconds for grey axvlines
    """
    cmap = matplotlib.cm.get_cmap("tab10")
    fig, ax = pyplot.subplots(figsize=(15, 6))
    if cols is None:
        cols = df.columns
    if title is not None:
        ax.set_title(title)
    if tags is not None:
        for tag in tags:
            timestamp = pd.to_datetime(tag, unit="s")
            if df.index.min() < timestamp < df.index.max():
                ax.axvline(timestamp, color="grey")
    for index, col in enumerate(cols):
        ax.plot(df.index, df[col], color=cmap(index), label=col)
        ax.set_xlabel("Time")
    fig.tight_layout()
    pyplot.legend()
    pyplot.show()


def plot_segments(
    dataframe: pd.DataFrame, segments: SyncPairs, together=True, seperate=True
):
    """
    Plot individual segments

    :param dataframe: the dataframe
    :param segments: a SyncPairs instance that specifies the data to be drawn
    :param together:
    :param seperate:
    """
    signal_names = list(segments.keys())
    segment_names = list(segments[signal_names[0]].keys())

    if together == seperate:
        raise ValueError("Set either `together` or `separate`")

    if together is True:
        # plot signals together
        ncols = 1
        nrows = len(segment_names)
        fig, axes = pyplot.subplots(nrows, ncols, figsize=(15, 4 * nrows))
        for segment_index, segment in enumerate(segment_names):
            axes[segment_index].set_title("{} segment".format(segment))
            signals_with_segment = [
                signal for signal in signal_names if segment in segments[signal]
            ]
            start = np.amin(
                [segments[x][segment]["start"] for x in signals_with_segment]
            )
            end = np.amax([segments[x][segment]["end"] for x in signals_with_segment])
            dataframe[start:end].plot(ax=axes[segment_index])
        fig.tight_layout()

    if seperate is True:
        # plot signals seperately
        ncols = len(segment_names)
        nrows = len(segments.keys())
        cmap = matplotlib.cm.get_cmap("tab10")
        fig, axes = pyplot.subplots(nrows, ncols, figsize=(15, 4 * nrows))
        for segment_index, signal_name in enumerate(segments.keys()):
            for index_seg, segment in enumerate(segment_names):
                if segment not in segments[signal_name]:
                    continue
                axes[segment_index, index_seg].set_title(
                    "{} segment of {}".format(segment, signal_name)
                )
                segment = segments[signal_name][segment]
                dataframe[signal_name][segment["start"] : segment["end"]].plot(
                    ax=axes[segment_index, index_seg], color=cmap(segment_index)
                )
        fig.tight_layout()


def plot_reference_columns(sources: SourceDict, title: str = ""):
    """
    Plots a normalized version of the reference columns, i.e., what jointly is detecting shakes on

    :param sources: a SourceDict
    :param title: additional title if desired
    """
    matplotlib.use("TkAgg")
    plt.figure(f"Test Debug: {title}")

    for device in sources:
        ref_column = sources[device]["ref_column"]
        data = sources[device]["data"][ref_column].dropna()
        data = data[data != 0]
        data = pd.Series(normalize(data.values), data.index)
        plt.plot(data.index, data, label=device)

    plt.legend()
    plt.show()
