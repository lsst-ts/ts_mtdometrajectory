.. py:currentmodule:: lsst.ts.MTDomeTrajectory

.. _lsst.ts.MTDomeTrajectory.developer_guide:

###############
Developer Guide
###############

The MTDomeTrajectory CSC is implemented using `ts_salobj <https://github.com/lsst-ts/ts_salobj>`_.

.. _lsst.ts.MTDomeTrajectory-api:

API
===

The primary classes are:

* `MTDomeTrajectory`: the CSC.
* `BaseAlgorithm`: base class for following algorithms.
* `SimpleAlgorithm`: a simple following algorithm.

.. automodapi:: lsst.ts.MTDomeTrajectory
   :no-main-docstr:

.. _lsst.ts.MTDomeTrajectory-build_and_test:

Build and Test
==============

This is a pure python package.
There is nothing to build except the documentation.

.. code-block:: bash

    make_idl_files.py MTDomeTrajectory
    setup -r .
    pytest -v  # to run tests
    package-docs clean; package-docs build  # to build the documentation

.. _lsst.ts.MTDomeTrajectory-contributing:

Contributing
============

``lsst.ts.MTDomeTrajectory`` is developed at https://github.com/lsst-ts/ts_MTDomeTrajectory.
You can find Jira issues for this module using `labels=ts_MTDomeTrajectory <https://jira.lsstcorp.org/issues/?jql=project%20%3D%20DM%20AND%20labels%20%20%3D%20ts_MTDomeTrajectory>`_.
