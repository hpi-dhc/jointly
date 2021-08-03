=======
jointly
=======


.. image:: https://img.shields.io/pypi/v/jointly.svg
        :target: https://pypi.python.org/pypi/jointly

.. image:: https://img.shields.io/travis/hpi-dhc/jointly.svg
        :target: https://travis-ci.org/hpi-dhc/jointly

.. image:: https://codecov.io/gh/hpi-dhc/jointly/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/hpi-dhc/jointly

.. image:: https://readthedocs.org/projects/jointly/badge/?version=latest
        :target: https://jointly.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://pyup.io/repos/github/hpi-dhc/jointly/shield.svg
     :target: https://pyup.io/repos/github/hpi-dhc/jointly/
     :alt: Updates



jointly is a python package for synchronizing sensors with accelerometer data.
Specifically, shake all your sensors in a box before and after a trial, and jointly will find these shakes, remove any temporal offset between sensors, and stretch the data so every clock aligns to a reference sensor.
Jointly ingests and produces ``pandas``' ``DataFrame`` objects.

* Free software: MIT license
* Documentation: https://jointly.readthedocs.io.


Features
--------

* detect and compare shakes in multiple sensor data streams
* remove temporal offsets in the data
* remove clock speed offsets by stretching the data

Usage
-----

Install the package from pypi:

.. code:: bash

    pip install jointly


The data has to be provided in pandas ``DataFrame`` instances with a
``DateTimeIndex`` for each sensor. In the following example, ``Faros`` and ``Empatica``
are two sensors we want to synchronize, and we have already prepared dataframes for them.
The Empatica is the reference source, and thus only the Faros' data will be changed in the output.


.. code:: python

    import jointly

    sources = {
        'Faros': {
            'data': faros_dataframe,
            'ref_column': 'acc_mag',
        },
        'Empatica': {
            'data': empatica_dataframe,
            'ref_column': 'acc_mag',
        }
    }
    reference_source_name = 'Empatica'

    extractor = jointly.ShakeExtractor()
    synchronizer = jointly.Synchronizer(sources, reference_source_name, extractor)
    synced_data = synchronizer.get_synced_data()
    synchronizer.save_pickles("./synced-files/")

Template Credits
----------------

This package was created with Cookiecutter_ and the `pyOpenSci/cookiecutter-pyopensci`_ project template, based off `audreyr/cookiecutter-pypackage`_.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`pyOpenSci/cookiecutter-pyopensci`: https://github.com/pyOpenSci/cookiecutter-pyopensci
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
