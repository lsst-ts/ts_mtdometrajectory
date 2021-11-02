.. py:currentmodule:: lsst.ts.mtdometrajectory

.. _lsst.ts.mtdometrajectory.developer_guide:

###############
Developer Guide
###############

The MTDomeTrajectory CSC is implemented using `ts_salobj <https://github.com/lsst-ts/ts_salobj>`_.

.. _lsst.ts.mtdometrajectory-api:

API
===

The primary classes are:

* `MTDomeTrajectory`: the CSC.
* `BaseAlgorithm`: base class for motion algorithms.
* `SimpleAlgorithm`: a simple motion algorithm.

.. automodapi:: lsst.ts.mtdometrajectory
   :no-main-docstr:

.. _lsst.ts.mtdometrajectory-build_and_test:

Build and Test
==============

This is a pure python package.
There is nothing to build except the documentation.

.. code-block:: bash

    make_idl_files.py MTDomeTrajectory
    setup -r .
    pytest -v  # to run tests
    package-docs clean; package-docs build  # to build the documentation

.. _lsst.ts.mtdometrajectory-contributing:

Contributing
============

``lsst.ts.mtdometrajectory`` is developed at https://github.com/lsst-ts/ts_mtdometrajectory.
You can find Jira issues for this module using `labels=ts_mtdometrajectory <https://jira.lsstcorp.org/issues/?jql=project%20%3D%20DM%20AND%20labels%20%20%3D%20ts_mtdometrajectory>`_.
