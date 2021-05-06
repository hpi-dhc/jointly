from typing import List, Tuple

import numpy as np
import pandas as pd
import scipy.signal
import scipy.interpolate
import pprint

from .abstract_extractor import AbstractExtractor
from .log import logger
from .synchronization_errors import (
    BadThresholdException,
    BadWindowException,
    ShakeMissingException,
)

pp = pprint.PrettyPrinter()


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

    def get_shake_weight(self, x):
        return np.median(x) + np.mean(x)

    def get_peak_sequences(self, signals, column, start_window, end_window):
        """Returns index list of peak sequences from a normalized signal.
        Peaks, that have no adjacent peaks within distance in milliseconds, are filtered.
        Sequences with a length less than min_length peaks are filtered.
        """
        sequences = []
        if not (0 <= self.threshold <= 1):
            raise BadThresholdException(
                "Threshold must be a value in [0, 1]. Data is normalized!"
            )

        logger.debug("Use peak threshold {}".format(self.threshold))

        start_part = signals[column].truncate(after=start_window)
        peaks_start, _properties = scipy.signal.find_peaks(
            start_part, height=self.threshold
        )

        end_part = signals[column].truncate(before=end_window)
        peaks_end, _properties = scipy.signal.find_peaks(
            end_part, height=self.threshold
        )
        peaks_end = peaks_end + signals.index.get_loc(end_part.index[0])

        peaks = [*peaks_start, *peaks_end]
        logger.debug("Found {} peaks for {}".format(len(peaks), column))

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
        logger.debug(
            "Merged peaks within {} ms to {} sequences for {}".format(
                self.distance, len(sequences), column
            )
        )

        # filter sequences with less than min_length peaks
        sequences_filtered = list(
            filter(lambda x: len(x) >= self.min_length, sequences)
        )
        logger.debug(
            "{} sequences did satisfy minimum length of {} for {}".format(
                len(sequences_filtered), self.min_length, column
            )
        )

        return sequences_filtered

    def _choose_sequence(self, signal, shake_list: List) -> Tuple:
        if len(shake_list) > 0:
            first = max(shake_list, key=self.get_shake_weight)
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

    def get_segments(self, signals):
        """Returns dictionary with timestamps, that mark start and end of each shake segment."""
        columns = list(signals.columns)
        self._init_segments(columns)
        # will be added to start and subtracted from end of sequence

        for column in columns:
            last_timestamp = signals[column].last_valid_index()
            first_timestamp = signals[column].first_valid_index()
            duration = last_timestamp - first_timestamp
            if duration < self.start_window_length or duration < self.end_window_length:
                raise BadWindowException(
                    f"The window is longer than signal {column}. Make it so the window only covers start and end, not both."
                )

            start_window = first_timestamp + self.start_window_length
            end_window = signals[column].last_valid_index() - self.end_window_length
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
