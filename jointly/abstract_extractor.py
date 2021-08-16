import abc
from typing import List

import pandas as pd

from jointly.types import SyncPairs


class AbstractExtractor(metaclass=abc.ABCMeta):
    """
    Super class for extractor methods.
    First subclass is the shake extractor, which finds the location of shakes in the data.
    """

    def __init__(self):
        self.segments = {}

    @abc.abstractmethod
    def get_segments(self, signals: pd.DataFrame) -> SyncPairs:
        """
        Detect first and second segments to use for synchronization and
        return dictionary with start and end timestamps for each signal.
        """

    def _init_segments(self, columns: List[str]):
        """Create a SynchronizationPair for each column"""
        self.segments = {}
        for column_name in columns:
            self.segments[column_name] = {
                "first": {},
                "second": {},
            }

    def _set_first_segment(
        self, column_name: str, start: pd.Timestamp, end: pd.Timestamp
    ):
        self.segments[column_name]["first"]["start"] = start
        self.segments[column_name]["first"]["end"] = end

    def _set_second_segment(
        self, column_name: str, start: pd.Timestamp, end: pd.Timestamp
    ):
        self.segments[column_name]["second"]["start"] = start
        self.segments[column_name]["second"]["end"] = end
