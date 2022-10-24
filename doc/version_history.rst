.. py:currentmodule:: lsst.ts.mtdometrajectory

.. _lsst.ts.mtdometrajectory.version_history:

###############
Version History
###############

v0.11.0
-------

* `MockDome`: use ``allow_missing_commands`` to simplify the code.
  This requires ts_salobj 7.2.
* ``Jenkinsfile``: change HOME to WHOME in most of it, to work with modern git.

Requires:

* ts_salobj 7.2
* ts_config_mttcs
* ts_simactuators 2
* ts_utils 1
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 12.1

v0.10.0
-------

* Rename command-line scripts to remove ".py" suffix.
* Build with pyproject.toml.

Requires:

* ts_salobj 7
* ts_config_mttcs
* ts_simactuators 2
* ts_utils 1
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 11.1

v0.9.3
------

* Modernize the Jenkinsfile.

Requires:

* ts_salobj 7
* ts_config_mttcs
* ts_simactuators 2
* ts_utils 1
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 11.1

v0.9.2
------

* Fix the case of the UPS file (was ts_MTDomeTrajectory.table).

Requires:

* ts_salobj 7
* ts_config_mttcs
* ts_simactuators 2
* ts_utils 1
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 11.1

v0.9.1
------

* Update for ts_xml 11.1, which is required.
  `MockDome`: ignore two additional commands.

Requires:

* ts_salobj 7
* ts_config_mttcs
* ts_simactuators 2
* ts_utils 1
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 11.1

v0.9.0
------

* Update for ts_salobj v7, which is required.
  This also requires ts_xml 11.

Requires:

* ts_salobj 7
* ts_config_mttcs
* ts_simactuators 2
* ts_utils 1
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 11

v0.8.0
------

* `MockDome` update for ts_xml 10.1, which is required.
* Rename package to ``ts_mtdometrajectory`` and Python namespace to ``lsst.ts.mtdometrajectory``.
* Update to use ts_utils.
* Add a ``Jenkinsfile``.
* Modernize unit tests to use bare asserts.
* Test black formatting with pytest-black instead of a custom unit test.

Requires:

* ts_salobj 6.3
* ts_config_mttcs
* ts_simactuators 2
* ts_utils 1
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 10.1

v0.7.0
------

* `MockDome`: add the ``exitFault`` command.
  This requires (and is required by) ts_xml 9.1.

Requires:

* ts_salobj 6.3
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 9.1

v0.6.0
------

* Support the ``setFollowingMode`` command.
  This requires ts_xml 9.
* `MTDomeTrajectory`: wait for the dome remote to start at startup,
  to avoid the CSC trying to command the dome before the remote is ready.
* ``test_csc.py``: eliminate several race conditions in ``make_csc``
   by waiting for the extra remotes and controllers to start.
* Change the CSC configuration schema to allow configuring all algorithms at once.
  This supports a planned change to how configuration files are read.
* Eliminate use of the abandoned ``asynctest`` package; use `unittest.IsolatedAsyncioTestCase` instead.
* Format the code with black 20.8b1.

Requires:

* ts_salobj 6.3
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 9.

v0.5.0
------

* Store the CSC configuration schema in code.
  This requires ts_salobj 6.3.
* `MockDome`: set the ``version`` class attribute.

Requires:

* ts_salobj 6.3
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 7.1.

v0.4.1
------

* `MTDomeTrajectory`: set the ``version`` class attribute.
  This sets the ``cscVersion`` field of the ``softwareVersions`` event.
* Modernize doc/conf.py for documenteer 0.6.

Requires:

* ts_salobj 6
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 7.1.

v0.4.0
------

* Updated for ts_xml 7.1 (which is required).
  Use ``MTMount`` instead of ``NewMTMount`` IDL.
* Updated to use ``pre-commit`` to check commits.

Requires:

* ts_salobj 6
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 7.1.

v0.3.0
------

* Removed deprecated flush argument when calling `lsst.ts.salobj.topics.ReadTopic.get`.
  This requires ts_salobj 6.
  
Requires:

* ts_salobj 6
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and MTDome

v0.2.1
------

* Update Jenkinsfile.conda to use the shared library.
* Pin the versions of ts_idl and ts_salobj in conda/meta.yaml.

Requires:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and MTDome

v0.2.0
------

* Implement renaming of Dome component to MTDome.

Requires:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and MTDome

v0.1.4
------

* Minor documentation fixes.

Requires:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome

v0.1.3
------

* Modernized the documentation.
* Use `lsst.ts.salobj.topics.ReadTopic.get`\ ``(flush=False)`` everywhere, to avoid deprecation warnings from ts_salobj.

Requires:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome

v0.1.2
------

* Fix a race condition in `MTDomeTrajectory`.
* Prevent the `MTDomeTrajectory` move_dome_* methods from hanging if an event is not received from the dome.
* Remove the ``simulation_mode`` argument from the `MTDomeTrajectory` constructor, since it was ignored.
* Add ``valid_simulation_modes`` class attribute to `MTDomeTrajectory` and `MockDome`.
* Lock version of black in meta.yaml.

Requires:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome


v0.1.1
------
Fix the conda build.

Requirements:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome

v0.1.0
------
Initial version.

Requirements:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome
