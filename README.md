# Jointly: Signal Synchronizer

## The Syncing Process

To sync two sources with each other, they need a simultaneously recorded signal with a characteristic signature at two timepoints in common. This could be the magnitude of the accelerometer for example, if multiple devices are shaken together.

### Selecting common segments

The script can detect prominent shakes automatically with the `ShakeExtractor`. This is done by detecting the peaks above a certain `threshold`. They are then merged to sequences, if two peaks are not farther apart than a specified `distance` in milliseconds. Sequences with less than `min_length` peaks are filtered out. Sequences, that do not start or end in a `window` of seconds from start and end of the signal respectivley, are filtered in a second step. From these filtered sequences the sequence with the highest weight (mean + median of sequence) is selected for the corresponding segment.

### Calculation of the timeshift

To compensate the differences in the system time of different sources, the timeshift to synchronize the selected segments with each other is calculated. For the automatic computation of the timeshift between two signals the cross-correlation for each segment with the reference signal is calculated. The signals are shifted so that the correlation between the selected segments is maximized.

### Adjusting the frequency

Due to clock drift, which denotes the issue that a clock is not running at the exact same frequency as a specified reference clock, signals that can be in sync at one timepoint desynchronize gradually over time. To compensate this effect a stretching factor is calculated, which brings the difference between the timeshifts for the synchronization based on the first and second segment respectively to zero. After stretching the signal, the timeshift to align the signals has to be calculated again.

## Example

### Syncing  data

The data has to be provided in pandas `DataFrame` with a `DateTimeIndex`.

```python
import jointly

sources = {
    'Faros': {
        'data': faros.data,
        'ref_column': 'acc_mag',
    },
    'Empatica': {
        'data': empatica.data,
        'ref_column': 'acc_mag',
    },
    'Everion': {
        'data': everion.data,
        'ref_column': 'acc_mag',
    }
}
ref_source_name = 'Empatica'

extractor = jointly.ShakeExtractor()
synchronizer = jointly.Synchronizer(sources, ref_source_name, extractor)
synced_data = synchronizer.get_synced_data()
```

### Saving data

To define the tables, which should be saved, create a dictionary. Every key at root level defines the name of the corresponding file. The dictionary at the second level defines a list of columns, which should be saved in this file, for each source. The `save_data()` method will also automatically save all data from all sources in a file named `TOTAL.csv`. This can be deactivated by adding the argument `save_total_table = False`.

```python
tables = {
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

synchronizer.save_data(sync_dir_path, tables=tables)
```

## Logging

To activate logging simply add the following lines to your code:

```python
from jointly.log import logger
logger.setLevel(10)
```

This will give you insight into the shake detection, calculation of the timeshifts and stretching factor, and output plots of the segements.