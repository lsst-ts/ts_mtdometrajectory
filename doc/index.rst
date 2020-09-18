.. py:currentmodule:: lsst.ts.MTDomeTrajectory

.. _lsst.ts.MTDomeTrajectory:

########################
lsst.ts.MTDomeTrajectory
########################

.. image:: https://img.shields.io/badge/Project Metadata-gray.svg
    :target: https://ts-xml.lsst.io/index.html#index-master-csc-table-mtdometrajectory
.. image:: https://img.shields.io/badge/SAL\ Interface-gray.svg
    :target: https://ts-xml.lsst.io/sal_interfaces/MTDomeTrajectory.html
.. image:: https://img.shields.io/badge/GitHub-gray.svg
    :target: https://github.com/lsst-ts/ts_MTDomeTrajectory
.. image:: https://img.shields.io/badge/Jira-gray.svg
    :target: https://jira.lsstcorp.org/issues/?jql=labels+%3D+ts_MTDomeTrajectory

Overview
========

MTDomeTrajectory moves the Simonyi Survey Telescope dome to follow the telescope.
It does this by reading telescope position from the `MTMount CSC`_ and issuing commands to the `Dome CSC`_.

Unlike most observatory enclosures, we plan to slowly rotate the dome during exposures, in order to minimize the time required to move to the next target.
MTDomeTrajectory supports multiple algorithms for determining how to move the dome, though at present only one simple algorithm is available.

.. _Dome CSC: https://ts-dome.lsst.io
.. _MTMount CSC: https://ts-mtmount.lsst.io

.. _lsst.ts.MTDomeTrajectory-user_guide:

User Guide
==========

Start the MTDomeTrajectory CSC as follows:

.. prompt:: bash

    run_mtdometrajectory.py

Stop the CSC by sending it to the OFFLINE state.

To make dome track the telescope send the MTDomeTrajectory CSC to the ENABLED state.

To stop the dome from tracking the telescope (e.g. if you want to send the dome to some specific position) send the MTDomeTrajectory CSC to the DISABLED state (or any state other than ENABLED).

MTDomeTrajectory supports multiple algorithms for moving the dome.
The algorithm is specified in the :ref:`configuration <lsst.ts.MTDomeTrajectory-configuration>`.

MTDomeTrajectory can be fully exercised without hardware by running the `MTMount CSC`_ and `Dome CSC`_ in simulation mode.
Thus MTDomeTrajectory does not need or have a simulation mode of its own.


.. _lsst.ts.MTDomeTrajectory-configuration:

Configuration
-------------

Configuration is defined by `this schema <https://github.com/lsst-ts/ts_MTDomeTrajectory/blob/develop/schema/MTDomeTrajectory.yaml>`_.
Configuration primarily consists of specifying the control algorithm and its associated parameters.

Available algorithms:

* `SimpleAlgorithm`

Configuration files live in `ts_config_mttcs/MTDomeTrajectory <https://github.com/lsst-ts/ts_config_mttcs/tree/develop/MTDomeTrajectory>`_.

Here is a sample configuration file that specifies all fields::

    # We strongly suggest that you specify the algorithm name
    # if you override any of the algorithm's default configuration.
    # That way your configuration file will continue to work
    # even if the default algorithm changes.
    algorithm_name: "simple"
    algorithm_config:
      # These two values are abitrary and merely for illustration.
      # Either or both can be omitted, and the defaults are reasonable.
      max_delta_azimuth: 3.5
      max_delta_elevation: 4

Developer Guide
===============

.. toctree::
    developer-guide
    :maxdepth: 1

Version History
===============

.. toctree::
    version_history
    :maxdepth: 1
