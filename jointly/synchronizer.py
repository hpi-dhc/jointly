import os
from typing import Dict, Optional

import numpy as np
import pandas as pd
from scipy.signal import correlate

from . import ShakeExtractor, helpers
from .abstract_extractor import AbstractExtractor
from .helpers import normalize, get_equidistant_signals
from .log import logger
from .synchronization_errors import StartEqualsEndError
from .types import SourceDict, ResultTableSpec, SyncPairTimeshift, SyncPairs


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
        """
        self.sources = sources
        self.ref_source_name = reference_source_name
        self._check_sources()

        self.extractor = extractor if extractor is not None else ShakeExtractor()
        self.ref_signals = self._prepare_ref_signals()

        self.sampling_freq = (
            sampling_freq
            if sampling_freq is not None
            else helpers.get_max_ref_frequency(self.ref_signals)
        )

    def _check_sources(self):
        """Verifies that the source dict adheres to the required format and that the reference source is available"""
        for source_name, source in self.sources.items():
            if "data" not in source or "ref_column" not in source:
                raise ValueError(
                    "Each source needs to have a `data` and a `ref_column` property"
                )
            if not isinstance(source["data"], pd.DataFrame):
                raise ValueError(
                    "The `data` property of each source must contain a DatFrame"
                )
            if not isinstance(source["data"].index, pd.DatetimeIndex):
                raise ValueError(
                    "The `data` DataFrame must have a pd.DatetimeIndex for each source"
                )
            if source["data"].index.duplicated().any():
                raise ValueError(
                    "The input dataframe must not have duplicate index values, "
                    "convert the data into a normalized wide format"
                )
            if (
                not isinstance(source["ref_column"], str)
                or source["ref_column"] not in source["data"].columns
            ):
                raise ValueError(
                    "Each source must have a string specifying the reference column, and the reference"
                    "column must be available in the source's DataFrame"
                )
        if self.ref_source_name not in self.sources.keys():
            raise ValueError(
                "The reference source name must be available in the source dict"
            )

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
        for index, segment in enumerate(["first", "second"]):
            logger.debug(
                f"Calculate timeshift of {segment} segment "
                f"for {sig_col} to {ref_col}."
            )

            # reference signal segment data extraction
            ref_start, ref_end, ref_data = helpers.get_segment_data(
                dataframe, segments, ref_col, segment
            )
            sig_start, sig_end, sig_data = helpers.get_segment_data(
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
        helpers.verify_segments(ref_signals.columns, sync_pairs)

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
                stretch_factor = helpers.get_stretch_factor(
                    sync_pairs[source], timeshifts
                )
            except ZeroDivisionError:
                raise StartEqualsEndError(
                    "First and last segment have been identified as exactly the same. Bad window, maybe?"
                )
            logger.info(f"Stretch factor for {source}: {stretch_factor}")

            # stretch signal and exchange it in dataframe
            signal_stretched = helpers.stretch_signals(
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
        helpers.verify_segments(stretched_ref_signals.columns, segments)

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
                data = helpers.stretch_signals(data, stretch_factor, start_time)
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
        if tables is not None and "SYNC" in tables.keys():
            raise ValueError(
                "SYNC must not be one of the table names. "
                "It is reserved for the synchronization parameters."
            )

        if save_total_table and tables is not None:
            if "TOTAL" in tables.keys():
                raise ValueError(
                    "TOTAL must not be one of the table names, "
                    "if the table with all data should be saved."
                )

        sync_params = self.get_sync_params()
        synced_data = self.get_synced_data()

        # Save sync params
        pd.DataFrame(sync_params).to_csv(os.path.join(target_dir, "SYNC.csv"))

        # Save custom tables
        logger.info(tables)
        if tables is not None:
            for table_name, table_spec in tables.items():
                if len(table_spec) == 0:
                    logger.warning(
                        f"Table entry {table_name} is missing any requested columns"
                    )
                    continue

                table_df = pd.DataFrame()

                for source_name, source_columns in table_spec.items():
                    # create dataframe for each source
                    source_df = pd.DataFrame()
                    for column in source_columns:
                        try:
                            data = synced_data[source_name][column]
                        except KeyError:
                            raise ValueError(
                                f"Requested non-existing {source_name}->{column}"
                            )
                        # join selected signals to device dataframe
                        source_df = source_df.join(data, how="outer")
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

            for source_name, data in synced_data.items():
                source_df = data.rename(
                    lambda col_name: f"{source_name}_{col_name}",
                    axis="columns",
                )
                total_table = total_table.join(source_df, how="outer")
            total_table.to_csv(os.path.join(target_dir, "TOTAL.csv"))
