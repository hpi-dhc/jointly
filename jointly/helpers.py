"""Contains signal processing and plotting helpers"""
from typing import List, Optional

import matplotlib.cm
import numpy as np
import pandas as pd
from matplotlib import pyplot, pyplot as plt

from jointly.types import SyncPairs, SourceDict


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
