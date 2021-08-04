==========
Background
==========

The Syncing Process
-------------------

To sync two sources with each other, they need a simultaneously recorded
signal with a characteristic signature at two timepoints in common. This
could be the magnitude of the accelerometer for example, if multiple
devices are shaken together.

Selecting common segments
~~~~~~~~~~~~~~~~~~~~~~~~~

The script can detect prominent shakes automatically with the
``ShakeExtractor``. This is done by detecting the peaks above a certain
``threshold``. These peaks are then merged into sequences of peaks that
are within ``distance`` milliseconds of each other. Sequence candidates
need to fulfill the following conditions:

* must have at least ``min_length`` peaks
* must be contained in ``start_window_length`` or ``end_window_length``, respectively

The sequence with the highest weight, i.e., ``mean + median`` of the peaks
in the sequence, is selected to represent the start- or end segment.

Calculation of the timeshift
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To compensate offsets in the system time of different sources,
the timeshift to synchronize the selected start segments with each other is
calculated. For the automatic computation of the timeshift between two
signals, the cross-correlation for each segment with the reference signal
is calculated. The signals are shifted so that the correlation between
the selected segments is maximized.

Adjusting the frequency
~~~~~~~~~~~~~~~~~~~~~~~

As no clock is perfect, an additional issue that arises when using multiple
sensors is that of clocks with an offset in running speed. While clock
speeds can drift over time, these influences are typically very small, and
it can generally be assumed that the offset from the correct speed is constant
for anything but long trials (Zhou, Hui, et al. "Frequency accuracy & stability
dependencies of crystal oscillators." Carleton University, Systems and Computer
Engineering, Technical Report SCE-08-12 (2008)).

The result of these differences in running speed is that signals desynchronize
over time. To compensate, a stretching factor is calculated, which brings
the difference between the synchronization timeshifts for the start- and end
segments to zero. After stretching the signal, the timeshift to remove the
offset between signals is removed again, resulting in the final timeshift
and stretch factor values.