.. highlight:: shell
.. _contributing_label:

============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

We would appreciate a feature suggestion issue before you create a PR so we can
discuss the feature, its use, and its implementation.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/hpi-dhc/jointly/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

jointly could always use more documentation, whether as part of the
official jointly docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/hpi-dhc/jointly/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `jointly` for local development.

1. Fork the `jointly` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/jointly.git

3. Install all dependencies after installing `poetry <https://python-poetry.org/docs/>`::

    $ cd jointly/
    $ poetry install
    $ pre-commit install

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass the tests and linters and that the docs can be built::

    $ py.test
    $ pre-commit run --all-files
    $ cd docs && make html


7. Commit your changes and then push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

8. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 3.7, 3.8 and 3.9, and for PyPi. This will be verified within the PR.

Tips
----

To run a subset of tests::

    $ py.test tests/test_examples.py


To run all tests::

    $ py.test

Deploying
---------

A reminder for the maintainers on how to deploy.
Make sure all your changes are committed, including an entry in HISTORY.rst and an update of the old version code
in ``docs/conf.py`` and ``pyproject.toml``.
Please also link the PR in your history entry.

GitHub will then deploy to PyPI if tests pass.
