from typing import Dict, Union, List

import pandas as pd

SourceDict = Dict[str, Dict[str, Union[str, pd.DataFrame, float, pd.Timedelta, None]]]
"""
A dictionary of dictionaries.
Each entry defines an input sensor, and points to a dictionary with the keys ``data`` and ``ref_column``.

``data`` is a pandas ``DataFrame`` with a ``DateTimeIndex``.

``ref_column`` specifies the column within ``data`` which should be used to extract synchronization points, e.g., shakes.
"""

SynchronizationPoint = Dict[str, pd.Timestamp]
"""
A dictionary describing a synchronization point, e.g., a shake.
A synchronization point has a start and an end, and thus the properties ``start`` and ``end``.
"""

SynchronizationPair = Dict[str, SynchronizationPoint]
"""
A dictionary containing both the first and the second synchronization point of a signal.
Two points are required to calculate the distance in between them.
Properties are ``first`` and ``second``.
"""

SyncPairs = Dict[str, SynchronizationPair]
"""
A dictionary that contains SynchronizationPair instances for a number of sources.
"""

SyncPairTimeshift = Dict[str, pd.Timedelta]
"""Timeshift for a single sync pair, i.e., the shift required to synchronize one pair to the reference signal"""

ResultTableSpec = Dict[str, Dict[str, List[str]]]
"""
Specification for saving the synchronized results in separated files, with each root key defining a target file.
The second level defines the columns which should be saved from each source file into the given target file.
This can be used to separate the input files into files containing only a single sensor type, e.g., to extract the
PPG signal from two different sensors into a single file.


Example:

.. code:: python

    {
        'ACC': {
            'Faros': ['Accelerometer_X', 'Accelerometer_Y', 'Accelerometer_Z'],
            'Empatica': ['acc_x', 'acc_y', 'acc_z'],
            'Everion': ['accx_data', 'accy_data', 'accz_data'],
        },
        'PPG': {
            'Empatica': ['bvp'],
            'Everion': ['blood_pulse_wave', 'led2_data', 'led3_data'],
        },
        'EDA': {
            'Empatica': ['eda'],
            'Everion': ['gsr_electrode'],
        },
        'ECG': {
            'Faros': ['ECG'],
        },
        'TEMP': {
            'Empatica': ['temp'],
            'Everion': ['temperature_object'],
        },
        'HR': {
            'Empatica': ['hr'],
            'Everion': ['heart_rate', 'heart_rate_quality'],
        },
        'IBI': {
            'Faros': ['HRV'],
            'Empatica': ['ibi'],
            'Everion': ['inter_pulse_interval', 'inter_pulse_interval_deviation'],
        }
    }

"""
