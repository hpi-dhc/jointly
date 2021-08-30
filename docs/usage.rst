==========
Usage
==========


Preparing Data for Ingestion
----------------------------

The data has to be provided in pandas ``DataFrame`` with a
``DateTimeIndex``. The following example shows how such a dataframe
should look:

.. code:: python

    import pandas as pd

    faros_df = pd.read_csv(
        "./test-data/faros-plus-physilog/faros.csv.gz",
        index_col=[0],
        parse_dates=True
    )
    print(faros_df.head())

The output of ``faros_df.head()`` shows that the index is a ``DateTimeIndex``.
The ``NaN`` values due to the different sampling frequencies are ignored during synchronization.

::

                             Accel X  Accel Y  Accel Z   ECG
    1970-01-01 00:00:01.000    -88.0    771.0   -531.5 -21.0
    1970-01-01 00:00:01.008      NaN      NaN      NaN -10.0
    1970-01-01 00:00:01.010    -86.0    779.0   -539.5   NaN
    1970-01-01 00:00:01.016      NaN      NaN      NaN  -2.0
    1970-01-01 00:00:01.020    -82.5    781.0   -543.0   NaN

Each signal source, i.e., each sensor,
is given in a dictionary together with the name of the column
containing the events that should be synchronized, e.g., the
shake common to all sensor signals in the acceleration magnitude.
The name of that column and its frequency can be different for
each sensor.

Finally, given the source dictionary, the synchronizer instance
can be created.

.. code:: python

    import jointly

    sources = {
        "Faros": {
            "data": faros_df,
            "ref_column": "Accel Mag",
        },
        "Physilog": {
            "data": physilog_df,
            "ref_column": "Accel Mag",
        },
        # Any number of sensors can be added
        # 'Everion': {
        #     'data': everion_dataframe,
        #     'ref_column': 'ACCELERATION_MAGNITUDE',
        # }
    }

    jointly.Synchronizer(sources, reference_source_name="Faros")

Tuning Shake Detection
----------------------

If the shake detection doesn't find all shakes on the first try,
the following parameters will help:

.. code:: python

    import pandas as pd
    import jointly

    extractor = jointly.ShakeExtractor()

    # The start window should be long enough to contain
    # only the start shake in every data stream
    extractor.start_window_length = pd.Timedelta(seconds=15)

    # The end window (measured from the end of data)
    # should be exactly long enough to contain
    # only the end shake in every data stream
    extractor.end_window_length = pd.Timedelta(seconds=3)

    # Set to at most the number of shakes you did
    extractor.min_length = 3

    # Shakes are only accepted if they are higher than the
    # threshold (with all data normalized).
    extractor.threshold = 0.5

Debugging
~~~~~~~~~

To find issues with the shake detection, it often helps to plot the data.
``plot_reference_columns`` is available to plot the reference columns from
a source table.

Problems during synchronization throw exceptions, such as a ``BadWindowException``:

    jointly.synchronization_errors.BadWindowException:

    Start (0 days 00:10:00) or end (0 days 00:10:00) window lengths greater than length of signal Faros (0 days 00:00:36.992000). Make it so each window only covers start or end, not both.

Thus, the following code catches the problem and prints/shows helpful information:

.. code:: python

    # if the extractor parameters are wrong, print the problem and show the data
    try:
        # get_synced_data returns a dictionary of sensor names to synced DataFrames
        synchronizer.get_synced_data()
    except Exception:
        traceback.print_exc()
        jointly.plot_reference_columns(sources)


Saving data
-----------

There are two approaches to saving the data. ``save_data()`` can be used
to create an export file for each data category, while ``save_pickles``
dumps the synchronized dataframes for each individual sensor into a ``.pickle``
each.

To run the following examples, you should already have a ``Synchronizer`` instance
called ``synchronizer`` with an extractor configured such that no exceptions are thrown.
Check the readme file for an example.

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
``['Accel X', 'Accel Y', 'Accel Z']``.

.. code:: python

    # define output format for two files, one containing all acceleration
    # data, the other the ECG data
    tables = {
        'ACC': {
            'Faros': ['Accel X', 'Accel Y', 'Accel Z'],
            'Physilog': ['Accel X', 'Accel Y', 'Accel Z'],
        },
        'ECG': {
            'Faros': ['ECG'],
        },
    }

    # if the extractor parameters are wrong, print the problem and show the data
    try:
        # get_synced_data returns a dictionary of sensor names to synced DataFrames
        with tempfile.TemporaryDirectory() as tmp_dir:
            synchronizer.save_data(tmp_dir, tables=tables, save_total_table=False)
            print("test")
    except Exception:
        traceback.print_exc()
        jointly.plot_reference_columns(sources)


In the resulting CSV file, each combination gets a column like this:
``Faros_Accel X``, or ``Physilog_Accel Z``, etc:

::

                                    Faros_Accel X    Faros_Accel Y    Faros_Accel Z    Physilog_Accel X    Physilog_Accel Y    Physilog_Accel Z
    1970-01-01 00:00:01.000000000             -88              771           -531.5
    1970-01-01 00:00:01.010000000             -86              779           -539.5
    1970-01-01 00:00:01.020000000           -82.5              781             -543
    1970-01-01 00:00:01.020907696                                                              -0.80457             0.02234             0.61023
    1970-01-01 00:00:01.030000000             -98              787           -521.5
    1970-01-01 00:00:01.040000000           -80.5              777             -557
    1970-01-01 00:00:01.050000000             -94            761.5           -539.5
    1970-01-01 00:00:01.052150462                                                              -0.81104             0.01721             0.59253



Logging
-------

To activate logging simply add the following lines to your code:

.. code:: python

    import logging
    from jointly.log import logger

    logger.setLevel(logging.DEBUG)

This will give you insight into the shake detection, calculation of the
timeshifts and stretching factor, and output plots of the segements.
