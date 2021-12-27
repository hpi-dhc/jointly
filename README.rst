==============
Jointly
==============


.. image:: https://img.shields.io/pypi/v/jointly.svg
        :target: https://pypi.python.org/pypi/jointly

.. image:: https://github.com/hpi-dhc/jointly/actions/workflows/deploy.yml/badge.svg
        :target: https://github.com/hpi-dhc/jointly/actions/workflows/deploy.yml?query=branch%3Amaster

.. image:: https://github.com/hpi-dhc/jointly/actions/workflows/all.yml/badge.svg
        :target: https://github.com/hpi-dhc/jointly/actions/workflows/all.yml?query=branch%3Amaster

.. image:: https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/enra64/f731de158a21515e2d6c52ed48d406ad/raw/jointly_coverage_main.json
        :target: https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/enra64/f731de158a21515e2d6c52ed48d406ad/raw/jointly_coverage_main.json

.. image:: https://readthedocs.org/projects/jointly/badge/?version=latest
        :target: https://jointly.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/hpi-dhc/jointly/shield.svg
     :target: https://pyup.io/repos/github/hpi-dhc/jointly/
     :alt: Updates

.. image:: https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg
     :target: https://github.com/hpi-dhc/jointly/blob/master/CODE_OF_CONDUCT.md
     
.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.5770586.svg
   :target: https://doi.org/10.5281/zenodo.5770586

Jointly is a python package for synchronizing sensors with accelerometer data.
You need this package if you're a researcher who has recorded accelerometer data (plus possibly other data) on multiple sensors and want to precisely synchronize the multiple data streams.
Specifically, shake all your sensors in a box before and after a trial, and jointly will find these shakes, remove any temporal offset between sensors, and stretch the data so every clock aligns to a reference sensor.
Jointly ingests and produces ``pandas`` ``DataFrame`` objects.

* Free software: MIT license
* Documentation: https://jointly.readthedocs.io


Features
--------

* detect and compare shakes in multiple sensor data streams
* remove temporal offsets in the data
* remove clock speed offsets by stretching the data

Installation
------------

Install the package from pypi:

.. code:: bash

    pip install jointly

You might want to check out our :ref:`contributing_label` guide in case you want to edit the package.

Usage
-----

The data has to be provided in pandas ``DataFrame`` instances with a
``DateTimeIndex`` for each sensor. In the following example, ``Faros`` and ``Empatica``
are two sensors we want to synchronize, and we have already prepared dataframes for them.
The Empatica is the reference source, and thus the Faros' data will be changed in the output.
The ``ref_column`` is the column that contains the characteristic shake, and all other columns
in the ``DataFrame`` will be synchronized together with that column.

.. code:: python

    import pandas as pd
    import tempfile
    import traceback

    import jointly

    # load source dataframes with datetime index
    faros_df = pd.read_csv(
        "./test-data/faros-plus-physilog/faros.csv.gz",
        index_col=[0],
        parse_dates=True
    )
    physilog_df = pd.read_csv(
        "./test-data/faros-plus-physilog/physilog.csv.gz",
        index_col=[0],
        parse_dates=True,
    )

    # the magnitude is a common property that keeps shake information without axis relevance
    faros_df["Accel Mag"] = jointly.calculate_magnitude(
        faros_df, ["Accel X", "Accel Y", "Accel Z"]
    )
    physilog_df["Accel Mag"] = jointly.calculate_magnitude(
        physilog_df, ["Accel X", "Accel Y", "Accel Z"]
    )

    # create dictionary of source sensors
    sources = {
        "Faros": {
            "data": faros_df,
            "ref_column": "Accel Mag",
        },
        "Physilog": {
            "data": physilog_df,
            "ref_column": "Accel Mag",
        },
    }

    # set shake extraction parameters
    extractor = jointly.ShakeExtractor()
    extractor.start_window_length = pd.Timedelta(seconds=15)
    extractor.end_window_length = pd.Timedelta(seconds=10)
    extractor.min_length = 3
    extractor.threshold = 0.55

    # prepare the synchronizer
    synchronizer = jointly.Synchronizer(
        sources, reference_source_name="Faros", extractor=extractor
    )

    # if the extractor parameters are wrong, print the problem and show the data
    try:
        # get_synced_data returns a dictionary of sensor names to synced DataFrames
        synchronizer.get_synced_data()
    except Exception:
        traceback.print_exc()
        jointly.plot_reference_columns(sources)

    # save a file for each input sensor somewhere
    with tempfile.TemporaryDirectory() as tmp_dir:
        synchronizer.save_pickles(tmp_dir)

Documentation Deep Links
~~~~~~~~~~~~~~~~~~~~~~~~

Here you can find more information on specific topics:

* `Preparing Data for Ingestion`_
* `Tuning the Shake Detection`_
* `Debugging the Shake Detection`_
* `How to Save the Synchronized Data`_
* `How to Enable Logging`_
* `Full Explanation of the Synchronization`_

Template Credits
----------------

This package was created with Cookiecutter_ and the `pyOpenSci/cookiecutter-pyopensci`_ project template, based off `audreyr/cookiecutter-pypackage`_.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`pyOpenSci/cookiecutter-pyopensci`: https://github.com/pyOpenSci/cookiecutter-pyopensci
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`Preparing Data for Ingestion`: https://jointly.readthedocs.io/en/latest/usage.html#preparing-data-for-ingestion
.. _`Tuning the Shake Detection`: https://jointly.readthedocs.io/en/latest/usage.html#tuning-shake-detection
.. _`Debugging the Shake Detection`: https://jointly.readthedocs.io/en/latest/usage.html#debugging
.. _`How to Save the Synchronized Data`: https://jointly.readthedocs.io/en/latest/usage.html#saving-data
.. _`How to Enable Logging`: https://jointly.readthedocs.io/en/latest/usage.html#logging
.. _`Full Explanation of the Synchronization`: https://jointly.readthedocs.io/en/latest/background.html#the-syncing-process

Citation
--------

Herdick, A., Musmann, F., Sasso, A., Albert, J., & Arnrich, B. (2021). Jointly: A Python package for synchronizing multiple sensors with accelerometer data (Version 1.0.3) [Computer software]. https://doi.org/https://doi.org/10.5281/zenodo.5770586
