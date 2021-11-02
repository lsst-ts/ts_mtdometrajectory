.. py:currentmodule:: lsst.ts.mtdometrajectory

.. _lsst.ts.mtdometrajectory:

########################
lsst.ts.mtdometrajectory
########################

.. image:: https://img.shields.io/badge/Project Metadata-gray.svg
    :target: https://ts-xml.lsst.io/index.html#index-master-csc-table-mtdometrajectory
.. image:: https://img.shields.io/badge/SAL\ Interface-gray.svg
    :target: https://ts-xml.lsst.io/sal_interfaces/MTDomeTrajectory.html
.. image:: https://img.shields.io/badge/GitHub-gray.svg
    :target: https://github.com/lsst-ts/ts_mtdometrajectory
.. image:: https://img.shields.io/badge/Jira-gray.svg
    :target: https://jira.lsstcorp.org/issues/?jql=labels+%3D+ts_mtdometrajectory

Overview
========

MTDomeTrajectory moves the Simonyi Survey Telescope dome to follow the telescope.
It does this by reading telescope position from the `MTMount CSC`_ and issuing commands to the `MTDome CSC`_.

Unlike most observatory enclosures, we plan to slowly rotate the dome during exposures, in order to minimize the time required to move to the next target.
MTDomeTrajectory supports multiple algorithms for determining how to move the dome, though at present only one simple algorithm is available.

.. _MTDome CSC: https://ts-mtdome.lsst.io
.. _MTMount CSC: https://ts-mtmount.lsst.io

.. _lsst.ts.mtdometrajectory-user_guide:

User Guide
==========

Start the MTDomeTrajectory CSC as follows:

.. prompt:: bash

    run_mtdometrajectory.py

Stop the CSC by sending it to the OFFLINE state.

To make the dome follow the telescope: issue the MTDomeTrajectory `setEnabledMode command`_ with ``enabled=True``.

To move the dome to a specified position that is different from the telescope:

* Stop the dome from following: issue the MTDomeTrajectory `setEnabledMode command`_ with ``enabled=False``.
* Move the dome: issue the MTDome `moveAz command`_ and/or `moveEl command`_.

MTDomeTrajectory can support multiple algorithms for making the dome follow the telescope;
but at the time of this writing, there is only one.
The algorithm is specified and configured in :ref:`configuration <lsst.ts.mtdometrajectory-configuration>`.

.. _setEnabledMode command: https://ts-xml.lsst.io/sal_interfaces/MTDomeTrajectory.html#setenabledmode
.. _moveAz command: https://ts-xml.lsst.io/sal_interfaces/MTDome.html#moveaz
.. _moveEl command: https://ts-xml.lsst.io/sal_interfaces/MTDome.html#moveel

Simulation
----------

MTDomeTrajectory can be fully exercised without hardware by running the `MTMount CSC`_ and `MTDome CSC`_ in simulation mode.
MTDomeTrajectory does not have a simulation mode of its own.

.. _lsst.ts.mtdometrajectory-configuration:

Configuration
-------------

Configuration is defined by `CONFIG_SCHEMA <https://github.com/lsst-ts/ts_mtdometrajectory/blob/develop/python/lsst/ts/mtdometrajectory/config_schema.py>`_.
Configuration primarily consists of specifying the control algorithm and its associated parameters.

.. _lsst.ts.mtdometrajectory-configuration-algorithms:

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
      # These two values are arbitrary and merely for illustration.
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
