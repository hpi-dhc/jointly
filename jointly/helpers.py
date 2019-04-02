import operator
import pandas as pd
import numpy as np
import matplotlib.cm
from matplotlib import pyplot

from .log import logger


### Signal processing

def normalize(x):
    """Normalizes signal to interval [-1, 1] with mean 0."""
    xn = x - np.mean(x)
    xn = xn / np.max(np.abs(xn))
    return xn

def get_equidistant_signals(signals, frequency):
    """Returns copy of dataframe with signals
    sampled equidistantly at the specified frequency.
    """
    freq = '{}us'.format(int(1e6 / frequency))
    df = pd.DataFrame(index=pd.date_range(start=pd.to_datetime(signals.index.min(), unit='s'),
                                        end=pd.to_datetime(signals.index.max(), unit='s'),
                                        freq=freq))
    df = df.join(signals.copy(), how='outer')
    df = df.interpolate(method='time').resample(freq).asfreq()
    return df


### Plotting

def plot_signals(df, cols=None, title=None, tags=None):
    cmap = matplotlib.cm.get_cmap('tab10')
    fig, ax = pyplot.subplots(figsize=(15, 6))
    if cols is None:
        cols = df.columns
    if title is not None:
        ax.set_title(title)
    if tags is not None:
        for tag in tags:
            timestamp = pd.to_datetime(tag, unit='s')
            if timestamp > df.index.min() and timestamp < df.index.max():
                ax.axvline(timestamp, color='grey')
    for index, col in enumerate(cols):
        ax.plot(df.index, df[col], color=cmap(index), label=col)
        ax.set_xlabel('Time')
    fig.tight_layout()
    pyplot.legend()
    pyplot.show()

def plot_segments(dataframe, segments, together=True, seperate=True):
    signal_names = list(segments.keys())
    segment_names = list(segments[signal_names[0]].keys())
    
    if together is True:
        # plot signals together
        ncols = 1
        nrows = len(segment_names)
        fig, axes = pyplot.subplots(nrows, ncols, figsize=(15, 4*nrows))
        for index, segment_name in enumerate(segment_names):
            axes[index].set_title('{} segment'.format(segment_name))
            signals_with_segment = list(filter(lambda x: segment_name in segments[x], signal_names))
            start = np.amin([segments[x][segment_name]['start'] for x in signals_with_segment])
            end = np.amax([segments[x][segment_name]['end'] for x in signals_with_segment])
            dataframe[start:end].plot(ax=axes[index])
        fig.tight_layout()
    
    if seperate is True:
        # plot signals seperately
        ncols = len(segment_names)
        nrows = len(segments.keys())
        cmap = matplotlib.cm.get_cmap('tab10')
        fig, axes = pyplot.subplots(nrows, ncols, figsize=(15, 4*nrows))
        for index, signal_name in enumerate(segments.keys()):
            for index_seg, segment_name in enumerate(segment_names):
                if segment_name not in segments[signal_name]:
                    continue
                axes[index, index_seg].set_title('{} segment of {}'.format(segment_name, signal_name))
                segment = segments[signal_name][segment_name]
                dataframe[signal_name][segment['start']:segment['end']] \
                    .plot(ax=axes[index, index_seg], color=cmap(index))
        fig.tight_layout()