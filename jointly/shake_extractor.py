from typing import List, Tuple

import numpy as np
import pandas as pd
import scipy.signal
import scipy.interpolate
import pprint

from . import SyncPairs
from .abstract_extractor import AbstractExtractor
from .log import logger
from .synchronization_errors import (
    BadThresholdException,
    BadWindowException,
    ShakeMissingException,
)

pp = pprint.PrettyPrinter()


def get_shake_weight(x):
    """Returns a shake weight describing the importance of a shake sequence"""
    return np.median(x) + np.mean(x)


class ShakeExtractor(AbstractExtractor):
    start_window_length = pd.Timedelta(seconds=600)
    """time window in seconds in which to look for peaks from start of signal"""

    end_window_length = pd.Timedelta(seconds=600)
    """time window in seconds in which to look for peaks at end of signal"""

    threshold = 0.3
    """min height for peak detection. In range [0, 1], as the data is normalized."""

    distance = 1500
    """distance in milliseconds in which the next peak must occur to be considered a sequence"""

    min_length = 6
    """minimum number of peaks per sequence"""

    time_buffer = pd.Timedelta(seconds=1)
    """time in seconds will be padded to first and last peak for timestamps of segment"""

    def _merge_peak_sequences(
        self, peaks: List[int], signals: pd.DataFrame
    ) -> List[List[int]]:
        """
        Merge the given peaks into peak sequences with inter-peak distances of less than ``self.distance``.

        :param peaks: list of peak indices
        :param signals: reference signals dataframe
        :return: list of lists, each inner list denotes a number of peaks by index
        """
        sequences = []
        for pos, index in enumerate(peaks):
            row = signals.iloc[[index]]
            if pos == 0:
                # start initial sequence
                sequences.append([row.index])
                continue
            row_prev = signals.iloc[[peaks[pos - 1]]]
            time = pd.to_datetime(row.index)
            time_prev = pd.to_datetime(row_prev.index)
            if time_prev + pd.Timedelta(milliseconds=self.distance) < time:
                # add peak to sequence, since this peak lies within distance of previous one
                sequences.append([row.index])
            else:
                # start new sequence
                sequences[len(sequences) - 1].append(row.index)
        return sequences

    def get_peak_sequences(
        self,
        signals: pd.DataFrame,
        column: str,
        start_window: pd.Timestamp,
        end_window: pd.Timestamp,
    ):
        """
        Returns index list of peak sequences from a normalized signal.
        Peaks that have no adjacent peaks within ``distance`` ms are ignored.
        Sequences with less than ``min_length`` peaks are ignored.
        """
        if not (0 <= self.threshold <= 1):
            raise BadThresholdException(
                "Threshold must be a value in [0, 1]. Data is normalized!"
            )

        logger.debug(f"Using peak threshold {self.threshold}")

        # find peaks in start window
        start_part = signals[column].truncate(after=start_window)
        peaks_start, _ = scipy.signal.find_peaks(start_part, height=self.threshold)

        # find peaks in end window
        end_part = signals[column].truncate(before=end_window)
        peaks_end, _ = scipy.signal.find_peaks(end_part, height=self.threshold)
        peaks_end += signals.index.get_loc(end_part.index[0])

        peaks = [*peaks_start, *peaks_end]
        logger.debug("Found {} peaks for {}".format(len(peaks), column))

        # merge peaks into peak sequences
        sequences = self._merge_peak_sequences(peaks, signals)
        logger.debug(
            f"Merged peaks within {self.distance} ms to "
            f"{len(sequences)} sequences for {column}"
        )

        # filter sequences with less than min_length peaks
        sequences_filtered = [seq for seq in sequences if len(seq) >= self.min_length]
        logger.debug(
            f"{len(sequences_filtered)} sequences satisfy"
            f" minimum length of {self.min_length} for {column}"
        )

        return sequences_filtered

    def _choose_sequence(self, signal: pd.Series, shake_list: List) -> Tuple:
        """

        :param signal:
        :param shake_list:
        :return:
        """
        if len(shake_list) > 0:
            first = max(shake_list, key=get_shake_weight)
            segment_start_time = first[0].index[0] - self.time_buffer
            segment_start_index = signal.index.get_loc(
                segment_start_time, method="nearest"
            )
            start = signal.index[segment_start_index]

            segment_end_time = first[-1].index[0] + self.time_buffer
            segment_end_index = signal.index.get_loc(segment_end_time, method="nearest")
            end = signal.index[segment_end_index]

            return start, end
        else:
            raise ShakeMissingException(f"No shakes detected")

    def get_segments(self, signals: pd.DataFrame) -> SyncPairs:
        """
        Returns dictionary with start and end for each sensor source, i.e., a ``SyncPairs`` instance

        :param signals: DataFrame containing the reference signals for each source
        :return: SyncPairs instance
        """
        columns = list(signals.columns)
        self._init_segments(columns)
        # will be added to start and subtracted from end of sequence

        for column in columns:
            last_timestamp = signals[column].last_valid_index()
            first_timestamp = signals[column].first_valid_index()
            duration = last_timestamp - first_timestamp
            if duration < self.start_window_length or duration < self.end_window_length:
                raise BadWindowException(
                    f"The window is longer than signal {column}. "
                    f"Make it so each window only covers start or end, not both."
                )

            start_window = first_timestamp + self.start_window_length
            end_window = last_timestamp - self.end_window_length
            peaks = self.get_peak_sequences(signals, column, start_window, end_window)

            # map peak indices to their values
            shakes = list(
                map(
                    lambda sequence: (
                        list(map(lambda index: signals[column][index], sequence))
                    ),
                    peaks,
                )
            )

            # select sequences in start/end window
            shakes_first = list(
                filter(lambda sequence: sequence[0].index[0] < start_window, shakes)
            )
            logger.debug(
                "{} shakes in before {} for {}.".format(
                    len(shakes_first), start_window, column
                )
            )
            shakes_second = list(
                filter(lambda sequence: sequence[-1].index[0] > end_window, shakes)
            )
            logger.debug(
                "{} shakes in after {} for {}.".format(
                    len(shakes_second), end_window, column
                )
            )

            # choose sequence with highest weight
            start, end = self._choose_sequence(signals[column], shakes_first)
            self._set_first_segment(column, start, end)

            start, end = self._choose_sequence(signals[column], shakes_second)
            self._set_second_segment(column, start, end)

            logger.info(
                "Shake segments for {}:\n{}".format(
                    column, pp.pformat(self.segments[column])
                )
            )

        return self.segments
