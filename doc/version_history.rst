.. py:currentmodule:: lsst.ts.MTDomeTrajectory

.. _lsst.ts.MTDomeTrajectory.version_history:

###############
Version History
###############

v0.4.0
======

Changes:

* Updated for ts_xml 7.1 (which is required).
  Use ``MTMount`` instead of ``NewMTMount`` IDL.
* Updated to use ``pre-commit`` to check commits.

Requires:

* ts_salobj 6
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory, MTDome, and MTMount built from ts_xml 7.1.

v0.3.0
======

Changes:

* Removed deprecated flush argument when calling `lsst.ts.salobj.topics.ReadTopic.get`.
  This requires ts_salobj 6.
  
Requires:

* ts_salobj 6
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and MTDome

v0.2.1
======

Changes:

* Update Jenkinsfile.conda to use the shared library.
* Pin the versions of ts_idl and ts_salobj in conda/meta.yaml.

Requires:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and MTDome

v0.2.0
======

Changes:

* Implement renaming of Dome component to MTDome.

Requires:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and MTDome

v0.1.4
======

Changes:

* Minor documentation fixes.

Requires:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome

v0.1.3
======

Changes:

* Modernized the documentation.
* Use `lsst.ts.salobj.topics.ReadTopic.get`\ ``(flush=False)`` everywhere, to avoid deprecation warnings from ts_salobj.

Requires:

* ts_salobj 5.15
* ts_config_mttcs
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome

v0.1.2
======

Changes:

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
