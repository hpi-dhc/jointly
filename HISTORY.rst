=======
History
=======

1.0.4 (2021-12-27)
------------------

* fix contributing.rst guide to testing
* improve documentation problems
* c.f. https://github.com/hpi-dhc/jointly/pull/12

1.0.3 (2021-12-09)
------------------

* remove poetry-core version dependency
* add information on running all tests to CONTRIBUTING.rst
* add a statement of need
* add documentation deep links to README.rst
* hopefully fix RTD build

1.0.2 (2021-08-04)
------------------

* Further improve CI/CD
* add documentation
* add badges
* add tests
* add more input validation
* changes some API parameter names and removes some functions

0.2.0 (2021-05-06)
------------------

* Improve CI/CD
* Various fixes

  * introduce ``black`` linter in repo
  * drastically reduce memory allocation by sequentially resampling
  * avoid OOM crash if debug/info plots are too large
  * seperately configurable start- and end-windoww lengths
  * handle error cases:

    * same start and end window
    * first or second shake missing

  * fix off-by-two error in shift index
  * add feature: per-sensor data exports in ``pickle`` format


0.1.3 - 0.1.5 (2019-09-10 to 2019-09-24)
----------------------------------------

* Minor Bugfixes
* Only look for peaks in window

0.1.2 (2019-08-26)
------------------

* Added parameter to interpolate only between valid values

0.1.1 (2019-05-16)
------------------

* Fixed get_synced_data()

0.1 (2019-05-09)
------------------

* Renamed methods to indicate internal only usage
* Fix truncation of data and remove auto truncation
* Improve readme
* Initial commit
* First release on PyPI.
