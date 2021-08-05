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


def _get_shake_weight(x: List[pd.DatetimeIndex]):
    """Returns a shake weight describing the importance of a shake sequence"""
    return np.median(x) + np.mean(x)


class ShakeExtractor(AbstractExtractor):
    def __init__(self):
        super().__init__()
        self.start_window_length = pd.Timedelta(seconds=600)
        self.end_window_length = pd.Timedelta(seconds=600)
        self.threshold = 0.6

    @property
    def start_window_length(self) -> pd.Timedelta:
        """time window as pandas.Timedelta in which to look for peaks from start of signal"""
        return self._start_window_length

    @start_window_length.setter
    def start_window_length(self, value: pd.Timedelta):
        if isinstance(value, pd.Timedelta):
            self._start_window_length = value
        else:
            raise ValueError(
                "window lengths are given as e.g. pd.Timedelta(seconds=600)"
            )

    @property
    def end_window_length(self) -> pd.Timedelta:
        """time window as pandas.Timedelta in which to look for peaks at end of signal"""
        return self._end_window_length

    @end_window_length.setter
    def end_window_length(self, value: pd.Timedelta):
        if isinstance(value, pd.Timedelta):
            self._end_window_length = value
        else:
            raise ValueError(
                "window lengths are given as e.g. pd.Timedelta(seconds=600)"
            )

    @property
    def threshold(self) -> float:
        """min height for peak detection. In range [0, 1], as the data is normalized"""
        return self._threshold

    @threshold.setter
    def threshold(self, value: float):
        if 0 < value < 1:
            self._threshold = value
        else:
            raise ValueError(f"threshold must be given in (0, 1), but you gave {value}")

    distance = 1500
    """distance in milliseconds in which the next peak must occur to be considered a sequence"""

    min_length = 6
    """minimum number of peaks per sequence"""

    time_buffer = pd.Timedelta(seconds=1)
    """time in seconds will be padded to first and last peak for timestamps of segment"""

    def _merge_peak_sequences(
        self, peaks: List[pd.DatetimeIndex], signals: pd.DataFrame
    ) -> List[List[pd.DatetimeIndex]]:
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

    def _get_peak_sequences(
        self,
        signals: pd.DataFrame,
        column: str,
        start_window: pd.Timestamp,
        end_window: pd.Timestamp,
    ) -> List[List[pd.DatetimeIndex]]:
        """
        Returns index list of peak sequences from a normalized signal.
        Peaks that have no adjacent peaks within ``distance`` ms are ignored.
        Sequences with less than ``min_length`` peaks are ignored.
        """
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

    def _choose_sequence(
        self, signal: pd.Series, shake_list: List[List[pd.DatetimeIndex]]
    ) -> Tuple[pd.Timestamp, pd.Timestamp]:
        """
        Choose the sequence with the highest shake weight

        :param signal: signal from which the shake is
        :param shake_list: list of peak sequence value lists
        :return: start and end index values
        """
        best_shake = max(shake_list, key=_get_shake_weight)

        segment_start_time = best_shake[0].index[0] - self.time_buffer
        start_index = signal.index.get_loc(segment_start_time, method="nearest")

        segment_end_time = best_shake[-1].index[0] + self.time_buffer
        end_index = signal.index.get_loc(segment_end_time, method="nearest")

        return signal.index[start_index], signal.index[end_index]

    @staticmethod
    def _check_shakes_not_empty(shakes: List[List[int]], label: str):
        """Raise an exception if the given list of shakes is empty"""
        if len(shakes) <= 0:
            raise ShakeMissingException(
                f"No {label} shakes detected - "
                "check window lengths, "
                "detection threshold, "
                "minimum sequence length"
            )

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
                    f"Start ({self.start_window_length}) or end ({self.end_window_length}) "
                    f"window lengths greater than length of signal {column} ({duration}). "
                    f"Make it so each window only covers start or end, not both."
                )

            start_window = first_timestamp + self.start_window_length
            end_window = last_timestamp - self.end_window_length
            peak_sequences = self._get_peak_sequences(
                signals, column, start_window, end_window
            )

            start_shakes, end_shakes, other_shakes = [], [], []
            for peak_sequence in peak_sequences:
                sequence_values = [signals[column][index] for index in peak_sequence]
                if sequence_values[0].index[0] < start_window:
                    start_shakes.append(sequence_values)
                elif sequence_values[-1].index[0] > end_window:
                    end_shakes.append(sequence_values)
                else:
                    other_shakes.append(sequence_values)

            # select sequences in start/end window
            logger.debug(
                f"{len(start_shakes)} shakes in start window ({start_window}), "
                f"{len(end_shakes)} shakes in end window ({end_window}), "
                f"{len(other_shakes)} shakes in between, for {column}."
            )

            ShakeExtractor._check_shakes_not_empty(start_shakes, "start")
            ShakeExtractor._check_shakes_not_empty(end_shakes, "end")

            # choose sequence with highest weight
            start, end = self._choose_sequence(signals[column], start_shakes)
            self._set_first_segment(column, start, end)

            start, end = self._choose_sequence(signals[column], end_shakes)
            self._set_second_segment(column, start, end)

            logger.info(
                f"Shake segments for {column}:\n{pp.pformat(self.segments[column])}"
            )

        return self.segments
