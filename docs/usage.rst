==========
Usage
==========


Syncing data
------------

The data has to be provided in pandas ``DataFrame`` with a
``DateTimeIndex``. Each signal source, i.e., each sensor,
is given in a dictionary together with the name of the column
containing the events that should be synchronized, e.g., the
shake common to all sensor signals in the acceleration magnitude.

.. code:: python

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

Tuning Shake Detection
----------------------

To optimize results of the shake detection, the following
parameters typically need to be adjusted:

.. code:: python

    extractor = jointly.ShakeExtractor()

    # this should contain only the start shakes in all data streams
    extractor.start_window_length = pd.Timedelta(seconds=N)

    # this should contain only the end shakes in all data streams
    extractor.end_window_length = pd.Timedelta(seconds=3)

    # the number of shakes that were done, e.g., 3
    extractor.min_length = 3

    # the minimum height of the shakes, in a normalized range
    extractor.threshold = 0.5

Debugging
~~~~~~~~~

To find issues with the shake detection, it often helps to plot the data.
``plot_reference_columns`` is available to plot the reference columns from
a source table.

.. code:: python

    try:
        jointly.Synchronizer(sources, reference_signal)
        sync_result = synchronizer.save_pickles(tmp_dir)
    except Exception:
        traceback.print_exc()
        plot_reference_columns(sources)


Saving data
-----------

There are two approaches to saving the data. ``save_data()`` can be used
to create an export file for each data category, while ``save_pickles``
dumps the synchronized dataframes for each individual sensor into a ``.pickle``
each.

``save_pickles()``
~~~~~~~~~~~~~~~~~~~~~~~

To save an individual DataFrame for each input source, call ``synchronizer.save_pickles()``


.. code:: python

    synchronizer.save_pickles(sync_dir_path)


``save_data()``
~~~~~~~~~~~~~~~~~~~~~~~

To use ``save_data()`` create a dictionary as follows: every
key at the root level defines the name of a corresponding file.
In each entry, select the source columns by creating a key (for
example, add ``Faros`` to select data from the ``Faros`` source)
that points to the columns to be extracted from that source, e.g.,
``['Accelerometer_X', 'Accelerometer_Y', 'Accelerometer_Z']``.

.. code:: python

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

    synchronizer.save_data(sync_dir_path, tables=tables, save_total_table=False)

Logging
-------

To activate logging simply add the following lines to your code:

.. code:: python

    from jointly.log import logger
    logger.setLevel(10)

This will give you insight into the shake detection, calculation of the
timeshifts and stretching factor, and output plots of the segements.
