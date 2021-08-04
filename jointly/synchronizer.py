import os
import logging
from pprint import pprint
from typing import Dict, Union, Optional, List, Tuple

import scipy.signal
import numpy as np
import pandas as pd
from matplotlib import pyplot

from . import ShakeExtractor, SyncPairs
from .log import logger
from .helpers import normalize, get_equidistant_signals
from .abstract_extractor import AbstractExtractor
from .synchronization_errors import ShakeMissingException, StartEqualsEndError
from .types import SourceDict, SyncPairTimeshift, ResultTableSpec


class Synchronizer:
    @property
    def extractor(self) -> AbstractExtractor:
        """Get the current extractor"""
        return self._extractor

    @extractor.setter
    def extractor(self, value: AbstractExtractor):
        if not issubclass(type(value), AbstractExtractor):
            raise TypeError("Extractor needs to be a subclass of AbstractExtractor.")
        self._extractor = value

    def __init__(
        self,
        sources: SourceDict,
        reference_source_name: str,
        extractor: Optional[AbstractExtractor] = None,
        sampling_freq: Optional[float] = None,
        tags=None,
    ):
        """
        Create a new synchronizer. Synchronizer objects are used to remove offsets and clock offsets by stretching and
        moving reference points detected by an extractor.

        :param sources: A SourceDict to describe the input data
        :param reference_source_name: name of the sensor to be used as reference.
               Other sensors will be made synchronous to this sensor, and data from this sensor will not be modified.
        :param extractor: This will be used to find synchronization points in the source data. If None, it defaults to
               a ShakeExtractor instance
        :param sampling_freq: Override the frequency used to resample input data. If None, it defaults to the maximum
               input frequency
        :param tags: TODO no idea
        """
        self.sources = sources
        self.ref_source_name = reference_source_name
        self.extractor = extractor if extractor is not None else ShakeExtractor()
        self.ref_signals = self._prepare_ref_signals()
        self.tags = tags

        self.sampling_freq = (
            sampling_freq if sampling_freq is not None else self.get_max_ref_frequency()
        )

    def truncate_data(self, buffer=300):
        if self.tags is None:
            return
        before = self.tags.data.index.min() - pd.Timedelta(seconds=buffer)
        after = self.tags.data.index.max() + pd.Timedelta(seconds=buffer)

        self.ref_signals = self.ref_signals.truncate(before=before, after=after)
        for source in self.sources.values():
            source["data"] = source["data"].truncate(before=before, after=after)

    def _prepare_ref_signals(self) -> pd.DataFrame:
        """
        Collect the reference columns from all sources and join them into a single dataframe.
        Each reference column is named equal to the name of the source it comes from.

        :return: normalized reference signals
        """
        reference_signals = pd.DataFrame()
        for source_name, source in self.sources.items():
            signal = source["data"][source["ref_column"]].dropna()
            reference_signals = reference_signals.join(signal, how="outer")
            reference_signals.rename(
                columns={source["ref_column"]: source_name}, inplace=True
            )
        reference_signals = reference_signals.apply(normalize)
        return reference_signals

    def get_max_ref_frequency(self) -> float:
        """
        Get the maximum frequency in the reference signals

        :return: float describing the maximum frequency in the source data.
        """
        if self.ref_signals is None:
            raise ValueError(
                "Unable to get maximum frequency: Reference signals undefined."
            )
        frequencies = self.ref_signals.aggregate(Synchronizer._infer_freq)
        return np.amax(frequencies)

    @staticmethod
    def _infer_freq(series: pd.Series) -> float:
        """
        Infer the frequency of a series by finding the median temporal distance between its elements.

        :param series: the frequency of this series will be inferred
        :return: frequency, as a float, measured in Hz
        """
        index = series.dropna().index
        timedeltas = index[1:] - index[:-1]
        median = np.median(timedeltas)
        return np.timedelta64(1, "s") / median

    @staticmethod
    def _stretch_signals(source: pd.DataFrame, factor: float, start_time=None):
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

    @staticmethod
    def _get_stretch_factor(segments, timeshifts):
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

    @staticmethod
    def _verify_segments(
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

    @staticmethod
    def _get_segment_data(
        dataframe: pd.DataFrame, segments: SyncPairs, col: str, segment: str
    ) -> Tuple[pd.Timestamp, pd.Timestamp, pd.DataFrame]:
        start = segments[col][segment]["start"]
        end = segments[col][segment]["end"]
        return start, end, dataframe[col][start:end]

    @staticmethod
    def _get_timeshift_pair(
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

        Synchronizer._verify_segments((ref_col, sig_col), segments, segment_names)

        fig, axes = None, None
        if logger.isEnabledFor(logging.INFO):
            fig, axes = pyplot.subplots(1, 2, figsize=(15, 4))

        for index, segment in enumerate(segment_names):
            logger.debug(
                f"Calculate timeshift of {segment} segment "
                f"for {sig_col} to {ref_col}."
            )

            # reference signal segment data extraction
            ref_start, ref_end, ref_data = Synchronizer._get_segment_data(
                dataframe, segments, ref_col, segment
            )
            sig_start, sig_end, sig_data = Synchronizer._get_segment_data(
                dataframe, segments, sig_col, segment
            )

            # calculate cross-correlation of segments
            cross_corr = scipy.signal.correlate(ref_data, sig_data)
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

    def _calculate_stretch_factors(self) -> pd.DataFrame:
        """
        Calculate the stretch factor that aligns each reference signal to the reference
        signal of the reference source. It immediately applies these stretch factors
        to a copy of ``self.ref_signals``.

        :return: a copy of self.ref_signals with the stretch factors applied.
        """
        ref_signals = self.ref_signals.copy()
        start_time = ref_signals.index.min()

        # Get equidistantly sampled reference signals for the cross correlation to work
        df_equidistant = get_equidistant_signals(ref_signals, self.sampling_freq)
        sync_pairs = self.extractor.get_segments(df_equidistant)

        for source in df_equidistant.columns:
            if source == self.ref_source_name:
                continue

            timeshifts = Synchronizer._get_timeshift_pair(
                df_equidistant, self.ref_source_name, source, sync_pairs
            )
            logger.debug(
                f"Timedelta between shifts before stretching: "
                f"{timeshifts['first'] - timeshifts['second']}"
            )
            try:
                stretch_factor = Synchronizer._get_stretch_factor(
                    sync_pairs[source], timeshifts
                )
            except ZeroDivisionError:
                raise StartEqualsEndError(
                    "First and last segment have been identified as exactly the same. Bad window, maybe?"
                )
            logger.info(f"Stretch factor for {source}: {stretch_factor}")

            # stretch signal and exchange it in dataframe
            signal_stretched = Synchronizer._stretch_signals(
                pd.DataFrame(ref_signals[source]).dropna(),
                stretch_factor,
                start_time,
            )
            ref_signals = (
                ref_signals.drop(source, axis="columns")
                .join(signal_stretched, how="outer")
                .astype(pd.SparseDtype("float"))
            )
            self.sources[source]["stretch_factor"] = stretch_factor

        return ref_signals

    def _calculate_timeshifts(self, stretched_ref_signals: pd.DataFrame):
        """
        Calculate the shift necessary to align the stretched reference signals to the not-stretched reference sensor.

        :param stretched_ref_signals: a copy of self.ref_signals that has been stretched to align the duration between
               the synchronization points to the duration between them in the reference sensor
        """
        # Resample again with stretched signal
        df_equi = get_equidistant_signals(stretched_ref_signals, self.sampling_freq)
        segments = self.extractor.get_segments(df_equi)

        for source in df_equi.columns:
            if source == self.ref_source_name:
                continue

            timeshifts = Synchronizer._get_timeshift_pair(
                df_equi, self.ref_source_name, source, segments
            )
            timedelta = timeshifts["first"] - timeshifts["second"]
            if timedelta > pd.Timedelta(0):
                logger.warning(
                    f"Timedelta between shifts after stretching: {timedelta}."
                    f"This should be very small: the timedelta to the reference signal"
                    f"should be equal for both start and end so a simple offset aligns the"
                    f"signals perfectly."
                )
            logger.info("Timeshift for {}: {}".format(source, timeshifts["first"]))
            self.sources[source]["timeshift"] = timeshifts["first"]

    def _calculate_sync_params(self):
        """
        This function calculates the synchronization parameters to sync all signals to the reference signal.
        It stores the result in ``self.sources``, in the keys ``timeshift`` and ``stretch_factor``.
        """
        self.sources[self.ref_source_name]["timeshift"] = None
        self.sources[self.ref_source_name]["stretch_factor"] = 1

        # Firstly, determine stretch factor and get stretched reference signals
        stretched_ref_signals = self._calculate_stretch_factors()

        # Secondly, get timeshift for the stretched signals
        self._calculate_timeshifts(stretched_ref_signals)

    def get_sync_params(self, recalculate: bool = False):
        """
        Get the synchronization params. If they have not been calculated yet, they will be.

        :param recalculate: force calculation, even if it was already done before
        :return: the synchronization params for each source, i.e., each timeshift and stretch factor
        """
        selected_keys = ["timeshift", "stretch_factor"]
        if recalculate or "timeshift" not in self.sources[self.ref_source_name]:
            self._calculate_sync_params()
        return {
            source_name: {
                key: value for key, value in source.items() if key in selected_keys
            }
            for source_name, source in self.sources.items()
        }

    def get_synced_data(self, recalculate: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Synchronize the input data.

        :param recalculate: force recalculating the synchronization parameters
        :return: a dictionary of the shifted and stretched source signals
        """
        self.get_sync_params(recalculate)
        synced_data = {}
        start_time = self.ref_signals.index.min()
        for source_name, source in self.sources.items():
            data = source["data"].copy()
            stretch_factor, timeshift = source["stretch_factor"], source["timeshift"]

            if stretch_factor != 1:
                data = Synchronizer._stretch_signals(data, stretch_factor, start_time)
            if timeshift is not None:
                data = data.shift(1, freq=timeshift)
            synced_data[source_name] = data
        return synced_data

    def save_pickles(self, target_dir: str) -> Dict[str, pd.DataFrame]:
        """
        Save a pickled, synced, dataframe for each source file.
        Does not save a total table.
        Sync parameters are saved as ``SYNC.csv``.

        :param target_dir: target directory for the export files
        :return: the synced data, plus a sync parameter dataframe in the dictionary entry with the key "SYNC".
        """
        sync_params = pd.DataFrame(self.get_sync_params())
        synced_data = self.get_synced_data()

        sync_params.to_csv(os.path.join(target_dir, "SYNC.csv"))

        for source_name, synced_df in synced_data.items():
            synced_df.to_pickle(
                os.path.join(target_dir, f"{source_name.upper()}.PICKLE")
            )

        return {**synced_data, "SYNC": sync_params}

    def save_data(
        self,
        target_dir: str,
        tables: Optional[ResultTableSpec] = None,
        save_total_table: bool = True,
    ):
        """
        Export synchronized data.
        Two formats are possible: if ``tables`` is given, a file for each root key is created containing the columns
        from the sensors specified as the keys on the second level. This can be used to create a file for each sensor
        type, see ``ResultTableSpec`` for an example.

        A ``SYNC.csv`` is always exported to store the synchronization parameters that have been calculated.

        :param target_dir: target directory for the export files
        :param tables: ResultTableSpec to specify the export format, or None
        :param save_total_table: exports an outer join over all synchronized dataframes
        """
        if "SYNC" in tables.keys():
            raise ValueError(
                "SYNC must not be one of the table names. It is reserved for the synchronization paramters."
            )

        if save_total_table and "TOTAL" in tables.keys():
            raise ValueError(
                "TOTAL must not be one of the table names, if the table with all data should be saved."
            )

        sync_params = self.get_sync_params()
        synced_data = self.get_synced_data()

        # Save sync params
        pd.DataFrame(sync_params).to_csv(os.path.join(target_dir, "SYNC.csv"))

        # Save custom tables
        logger.info(tables)
        if tables is not None:
            for table_name, table_spec in tables.items():
                table_df = pd.DataFrame()
                if self.tags is not None:
                    table_df = table_df.join(self.tags.data, how="outer")

                for source_name, source_columns in table_spec.items():
                    # create dataframe for each source
                    source_df = pd.DataFrame()
                    for column in source_columns:
                        if column in synced_data[source_name].columns:
                            # join selected signals to device dataframe
                            source_df = source_df.join(
                                synced_data[source_name][column], how="outer"
                            )
                        else:
                            logger.warning(
                                f"Requested non-existing {column} from {source_name}"
                            )
                    if not source_df.empty:
                        # add device signals to general dataframe
                        source_df = source_df.rename(
                            lambda col_name: f"{source_name}_{col_name}",
                            axis="columns",
                        )
                        table_df = table_df.join(source_df, how="outer")

                table_df.dropna(axis="index", how="all", inplace=True)
                table_df.to_csv(os.path.join(target_dir, f"{table_name}.csv"))

        # Save table with total data
        if save_total_table:
            total_table = pd.DataFrame()
            if self.tags is not None:
                total_table = total_table.join(self.tags.data, how="outer")
            for source_name, data in synced_data.items():
                source_df = data.rename(
                    lambda col_name: f"{source_name}_{col_name}",
                    axis="columns",
                )
                total_table = total_table.join(source_df, how="outer")
            total_table.to_csv(os.path.join(target_dir, "TOTAL.csv"))
