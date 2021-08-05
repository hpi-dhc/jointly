"""Contains plotting helpers"""
from typing import List, Optional

import matplotlib.cm
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from jointly import normalize
from jointly.types import SyncPairs, SourceDict


def plot_segments(
    dataframe: pd.DataFrame, segments: SyncPairs, together=False, separate=False
):
    """
    Plot the segments of a reference signal dataframe

    :param dataframe: the dataframe
    :param segments: a SyncPairs instance that specifies the data to be drawn
    :param together: true to plot everything together
    :param separate: true to plot separate
    """
    signal_names = list(segments.keys())
    segment_names = list(segments[signal_names[0]].keys())

    if together == separate:
        raise ValueError("Set either `together` or `separate`")

    if together is True:
        # plot signals together
        ncols = 1
        nrows = len(segment_names)
        fig, axes = plt.subplots(nrows, ncols, figsize=(15, 4 * nrows))
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

    if separate is True:
        # plot signals seperately
        ncols = len(segment_names)
        nrows = len(segments.keys())
        cmap = matplotlib.cm.get_cmap("tab10")
        fig, axes = plt.subplots(nrows, ncols, figsize=(15, 4 * nrows))
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

    plt.show()


def plot_reference_columns(sources: SourceDict, title: str = ""):
    """
    Plots a normalized version of the reference columns, i.e., what jointly is detecting shakes on

    :param sources: a SourceDict
    :param title: additional title if desired
    """
    plt.figure(f"Test Debug: {title}")

    for device in sources:
        ref_column = sources[device]["ref_column"]
        data = sources[device]["data"][ref_column].dropna()
        data = data[data != 0]
        data = pd.Series(normalize(data.values), data.index)
        plt.plot(data.index, data, label=device)

    plt.legend()
    plt.show()
