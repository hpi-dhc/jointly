import numpy as np
import pandas as pd
import scipy.signal
import scipy.interpolate
import pprint

from .abstract_extractor import AbstractExtractor
from .log import logger

pp = pprint.PrettyPrinter()

class ShakeExtractor(AbstractExtractor):

    window = 300
    """time window in seconds in which to look for peaks from start and end of signal"""
    threshold = 0.3
    """threshold for peak detection"""
    distance = 1500
    """distance in milliseconds in which the next peak must occur to be considered a sequence"""
    min_length = 6
    """minimum number of peaks per sequence"""
    time_buffer = 1
    """time in seconds will be padded to first and last peak"""

    def get_shake_weight(self, x):
        return np.median(x) + np.mean(x)

    def get_peak_sequences(self, signals, column):
        """Returns index list of peak sequences from a normalized signal.
        Peaks, that have no adjacent peaks within distance in milliseconds, are filtered.
        Sequences with a length less than min_length peaks are filtered.
        """
        sequences = []
        logger.debug('Use peak threshold {}'.format(self.threshold))
        
        peaks, _properties = scipy.signal.find_peaks(signals[column], height=self.threshold)
        logger.debug('Found {} peaks for {}'.format(len(peaks), column))
        
        for pos, index in enumerate(peaks):
            row = signals.iloc[[index]]
            if pos==0:
                # start initial sequence
                sequences.append([row.index])
                continue
            row_prev = signals.iloc[[peaks[pos-1]]]
            time = pd.to_datetime(row.index)
            time_prev = pd.to_datetime(row_prev.index)
            if time_prev + pd.Timedelta(milliseconds=self.distance) < time:
                # add peak to sequence, since this peak lies within distance of previous one
                sequences.append([row.index])
            else:
                # start new sequence
                sequences[len(sequences)-1].append(row.index)
        logger.debug('Merged peaks within {} ms to {} sequences for {}'.format(self.distance, len(sequences), column))
        
        # filter sequences with less than min_length peaks
        sequences_filtered = list(filter(lambda x: len(x) >= self.min_length, sequences))
        logger.debug('{} sequences did satisfy minimum length of {} for {}'.format(len(sequences_filtered), self.min_length, column))
        
        return sequences_filtered

    def get_segments(self, signals):
        """Returns dictionary with timestamps, that mark start and end of each shake segment."""
        columns = list(signals.columns)
        self._init_segments(columns)
        time_buffer = pd.Timedelta(seconds=self.time_buffer) # will be added to start and subtracted from end of sequence
        window = pd.Timedelta(seconds=self.window) # time window from start and end in which to look for sequences

        for column in columns:
            peaks = self.get_peak_sequences(signals, column)
            # map peak indices to their values
            shakes = list(map(lambda sequence: (list(map(lambda index: signals[column][index], sequence))), peaks))
            
            # select sequences in start/end window
            start_window = signals[column].first_valid_index() + window
            end_window = signals[column].last_valid_index() - window
            shakes_first = list(filter(lambda sequence: sequence[0].index[0] < start_window, shakes))
            logger.debug('{} shakes in before {} for {}.'.format(len(shakes_first), start_window, column))
            shakes_second = list(filter(lambda sequence: sequence[-1].index[0] > end_window, shakes))
            logger.debug('{} shakes in after {} for {}.'.format(len(shakes_second), end_window, column))
            
            # choose sequence with highest weight
            if len(shakes_first) > 0:
                first = max(shakes_first, key=self.get_shake_weight)
                start = first[0].index[0] - time_buffer
                end = first[-1].index[0] + time_buffer
                self._set_first_segment(column, start, end)
            if len(shakes_second) > 0:
                second = max(shakes_second, key=self.get_shake_weight)
                start = second[0].index[0] - time_buffer
                end = second[-1].index[0] + time_buffer
                self._set_second_segment(column, start, end)
            logger.info('Shake segments for {}:\n{}'.format(column, pp.pformat(self.segments[column])))
        
        return self.segments
    