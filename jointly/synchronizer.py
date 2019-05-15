import os
import logging
import numbers
import scipy.signal
import numpy as np
import pandas as pd
from matplotlib import pyplot

from .log import logger
from .helpers import normalize, get_equidistant_signals
from .abstract_extractor import AbstractExtractor

class Synchronizer:
    @property
    def extractor(self):
        return self._extractor

    @extractor.setter
    def extractor(self, value):
        if not issubclass(type(value), AbstractExtractor):
            raise TypeError('Extractor needs to be a subclass of AbstractExtractor.')
        self._extractor = value

    def __init__(self, sources, ref_source_name, extractor, sampling_freq=None, tags=None): 
        self.sources = sources
        self.ref_source_name = ref_source_name
        self.extractor = extractor
        self.ref_signals = self._prepare_ref_signals()
        self.tags = tags

        if sampling_freq is not None:
            self.sampling_freq = sampling_freq
        else:
            self.sampling_freq = self.get_max_ref_frequency()

    def truncate_data(self, buffer=300):
        if self.tags is None:
            return
        before = self.tags.data.index.min() - pd.Timedelta(seconds=buffer)
        after = self.tags.data.index.max() + pd.Timedelta(seconds=buffer)

        self.ref_signals = self.ref_signals.truncate(before=before, after=after)
        for source in self.sources.values():
            source['data'] = source['data'].truncate(before=before, after=after)

    def _prepare_ref_signals(self):
        ref_signals = pd.DataFrame()
        for source_name, source in self.sources.items():
            signal = source['data'][source['ref_column']].dropna()
            ref_signals = ref_signals.join(signal, how='outer')
            ref_signals.rename(columns=(lambda x: source_name if x == source['ref_column'] else x), inplace=True)
        ref_signals = ref_signals.apply(normalize)            
        return ref_signals
    
    def get_max_ref_frequency(self):
        if self.ref_signals is None:
            raise ValueError('Unable to get maximum frequency: Reference signals undefined.')
        frequencies = self.ref_signals.aggregate(Synchronizer._infer_freq)
        return np.amax(frequencies)

    @staticmethod
    def _infer_freq(series):
        index = series.dropna().index
        timedeltas = index[1:] - index[:-1]
        median = np.median(timedeltas)
        return np.timedelta64(1, 's') / median

    @staticmethod
    def _stretch_signals(source, factor, start_time=None):
        """Returns copy of DataFrame with stretched DateTimeIndex."""
        df = source.copy()
        if start_time is None:
            start_time = df.index.min()
        logger.debug('Use start time: {}'.format(start_time))
        timedelta = df.index - start_time
        new_index = timedelta * factor + start_time
        df.set_index(new_index, inplace=True, verify_integrity=True)
        return df

    @staticmethod
    def _get_stretch_factor(segments, timeshifts):
        old_length = segments['second']['start'] - segments['first']['start']
        new_length = old_length + timeshifts['second'] - timeshifts['first']
        stretch_factor = new_length / old_length
        return stretch_factor

    @staticmethod
    def _get_timeshifts(dataframe, columns, segments):
        """Returns timeshifts to synchronize columns[1] with columns[0].
        First signal in columns will be used as reference.
        Expects equidistant sampled signals.
        """
        timeshifts = {}
        segment_names = ['first', 'second']
        ref_column = columns[0]
        sig_column = columns[1]
        
        if logger.isEnabledFor(logging.INFO):
            fig, axes = pyplot.subplots(1, 2, figsize=(15, 4))

        for index, segment in enumerate(segment_names):
            logger.debug('Calculate timeshift of {} segment for {} to {}.'.format(segment, sig_column, ref_column))
            
            # get segments from both signals
            ref_start = segments[ref_column][segment]['start']
            ref_end = segments[ref_column][segment]['end']
            ref_segment = dataframe[ref_column][ref_start:ref_end]

            sig_start = segments[sig_column][segment]['start']
            sig_end = segments[sig_column][segment]['end']
            sig_segment = dataframe[sig_column][sig_start:sig_end]
                    
            # calculate cross-correlation of segments
            cross_corr = scipy.signal.correlate(ref_segment, sig_segment)
            # get shift in samples
            shift_in_samples = np.argmax(cross_corr) - len(sig_segment) - 1
            # get timestamp at which sig_segment must start to sync signals
            max_corr_ts = dataframe.index[dataframe.index.get_loc(ref_start) + shift_in_samples]
            logger.debug('Highest correlation with start at {} with {}.'.format(max_corr_ts, np.max(cross_corr)))
            
            # calculate timeshift to move signal to maximize correlation
            timeshifts[segment] = max_corr_ts - sig_start
            logger.debug('Timeshift is {}.'.format(str(timeshifts[segment])))
            
            # plot shifted segments
            if logger.isEnabledFor(logging.INFO):
                df = dataframe.copy()
                df[sig_column] = df[sig_column].shift(1, freq=timeshifts[segment])
                axes[index].set_title('{} segment of {c[0]} and {c[1]}'.format(segment, c=columns))
                df[columns][ref_start:ref_end].plot(ax=axes[index])

        if logger.isEnabledFor(logging.INFO):
            fig.tight_layout()

        return timeshifts

    def _calculate_sync_params(self):
        dataframe = self.ref_signals.copy()
        start_time = self.ref_signals.index.min()
        self.sources[self.ref_source_name]['timeshift'] = None
        self.sources[self.ref_source_name]['stretch_factor'] = 1

        # Interpolate and resample to equidistant signal
        df_equi = get_equidistant_signals(self.ref_signals, self.sampling_freq)
        segments = self.extractor.get_segments(df_equi)

        # First round to determine stretch factor
        for column in df_equi.columns:
            if column == self.ref_source_name:
                continue
            else:
                timeshifts = Synchronizer._get_timeshifts(df_equi, [self.ref_source_name, column], segments)
                logger.debug('Timedelta between shifts before stretching: {}'.format(timeshifts['first'] - timeshifts['second']))
                self.sources[column]['stretch_factor'] = Synchronizer._get_stretch_factor(segments[column], timeshifts)
                logger.info('Stretch factor for {}: {}'.format(column, self.sources[column]['stretch_factor']))
                
                # stretch signal and exchange it in dataframe
                signal_stretched = Synchronizer._stretch_signals(pd.DataFrame(dataframe[column]), self.sources[column]['stretch_factor'], start_time)
                dataframe = dataframe.drop(column, axis='columns').join(signal_stretched, how='outer')

        # Resample again with stretched signal
        df_equi = get_equidistant_signals(dataframe, self.sampling_freq)
        segments = self.extractor.get_segments(df_equi)

        # Second round to get timeshift for stretched signal
        for column in df_equi.columns:
            if column == self.ref_source_name:
                continue
            else:
                timeshifts = Synchronizer._get_timeshifts(df_equi, [self.ref_source_name, column], segments)
                timedelta = timeshifts['first'] - timeshifts['second']
                if timedelta > pd.Timedelta(0):
                    logger.warning('Timedelta between shifts after stretching: {}'.format(timedelta))
                logger.info('Timeshift for {}: {}'.format(column, timeshifts['first']))
                self.sources[column]['timeshift'] = timeshifts['first']

    def get_sync_params(self, recalculate=False):
        selected_keys = ['timeshift', 'stretch_factor']
        if recalculate or 'timeshift' not in self.sources[self.ref_source_name]:
            self._calculate_sync_params()
        return {
            source_name: {
                key: value for key, value in source.items() if key in selected_keys
            } for source_name, source in self.sources.items()}

    def get_synced_data(self, recalculate=False):
        self.get_sync_params(recalculate)
        synced_data = {}
        start_time = self.ref_signals.index.min()
        for source_name, source in self.sources.items():
            data = source['data'].copy()
            if source['stretch_factor'] is not 1:
                data = Synchronizer._stretch_signals(data, source['stretch_factor'], start_time)
                data = data.shift(1, freq=source['timeshift'])
            synced_data[source_name] = data
        return synced_data
    
    def save_data(self, path, tables=None, save_total_table=True):
        if 'SYNC' in tables.keys():
            raise ValueError('SYNC must not be one of the table names. It is reserved for the synchronization paramters.')

        if save_total_table and 'TOTAL' in tables.keys():
            raise ValueError('TOTAL must not be one of the table names, if the table with all data should be saved.')
        
        sync_params = self.get_sync_params()
        synced_data = self.get_synced_data()

        # Save sync params
        pd.DataFrame(sync_params).to_csv(os.path.join(path, 'SYNC.csv'))

        # Save custom tables
        logger.info(tables)
        if tables is not None:
            for table_name, table_spec in tables.items():
                table_df = pd.DataFrame()
                if self.tags is not None:
                    table_df = table_df.join(self.tags.data, how='outer')
                for source_name, source_columns in table_spec.items():
                    # create dataframe for each source
                    source_df = pd.DataFrame()
                    for column in source_columns:
                        if column in synced_data[source_name].columns:
                            # join selected signals to device dataframe
                            source_df = source_df.join(synced_data[source_name][column], how='outer')
                    if not source_df.empty:
                        # add device signals to general dataframe
                        source_df = source_df.rename(lambda x: '{prefix}_{column}'.format(prefix=source_name, column=x), axis='columns')
                        table_df = table_df.join(source_df, how='outer')
                table_df.dropna(axis='index', how='all', inplace=True)
                table_df.to_csv(os.path.join(path, '{filename}.csv'.format(filename=table_name)))

        # Save table with total data
        if save_total_table:
            total_table = pd.DataFrame()
            if self.tags is not None:
                total_table = total_table.join(self.tags.data, how='outer')
            for source_name, data in synced_data.items():
                source_df = data.rename(lambda x: '{prefix}_{column}'.format(prefix=source_name, column=x), axis='columns')
                total_table = total_table.join(source_df, how='outer')
            total_table.to_csv(os.path.join(path, 'TOTAL.csv'))
