# Jointly - Signal Synchronizer

## The Syncing Process

To sync two sources with each other, they need a simultaneously recorded signal with a characteristic signature at two timepoints in common. This could be the magnitude of the accelerometer for example, if multiple devices are shaken together.

### Selecting common segments

The script can detect prominent shakes automatically with the `ShakeExtractor`. This is done by detecting the peaks above a certain `threshold`. They are then merged to sequences, if two peaks are not farther apart than a specified `distance` in milliseconds. Sequences with less than `min_length` peaks are filtered out. Sequences, that do not start or end in a `window` of seconds from start and end of the signal respectivley, are filtered in a second step. From these filtered sequences the sequence with the highest weight (mean + median of sequence) is selected for the corresponding segment.

### Calculation of the timeshift

To compensate the differences in the system time of different sources, the timeshift to synchronize the selected segments with each other is calculated. For the automatic computation of the timeshift between two signals the cross-correlation for each segment with the reference signal is calculated. The signals are shifted so that the correlation between the selected segments is maximized.

### Adjusting the frequency

Due to clock drift, which denotes the issue that a clock is not running at the exact same frequency as a specified reference clock, signals that can be in sync at one timepoint desynchronize gradually over time. To compensate this effect a stretching factor is calculated, which brings the difference between the timeshifts for the synchronization based on the first and second segment respectively to zero. After stretching the signal, the timeshift to align the signals has to be calculated again.

## Example

```python
import jointly

devices = {
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
ref_device_name = 'Empatica'

extractor = jointly.ShakeExtractor()
synchronizer = jointly.Synchronizer(devices, ref_device_name, extractor)
synced_data = synchronizer.get_synced_data()
```