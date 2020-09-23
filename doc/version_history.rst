.. py:currentmodule:: lsst.ts.MTDomeTrajectory

.. _lsst.ts.MTDomeTrajectory.version_history:

###############
Version History
###############

v0.1.4
======

Changes:

* Minor documentation fixes.

Requires:

* Dome
* ts_salobj 5.15
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome

v0.1.3
======

Changes:

* Modernized the documentation.
* Use `lsst.ts.salobj.topics.ReadTopic.get(flush=False)` everywhere, to avoid deprecation warnings from ts_salobj.

Requires:

* Dome
* ts_salobj 5.15
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome

v0.1.2
======

Changes:

* Fix a race condition in `MTDomeTrajectory`.
* Prevent the `MTDomeTrajectory` move_dome_* methods from hanging if an event is not received from the dome.
* Remove the ``simulation_mode`` argument from the `MTDomeTrajectory` constructor, since it was ignored.
* Add `valid_simulation_modes` class attribute to `MTDomeTrajectory` and `MockDome`.
* Lock version of black in meta.yaml.

Requires:

* Dome
* ts_salobj 5.15
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome


v0.1.1
------
Fix the conda build.

Requirements:

* Dome
* ts_salobj 5.15
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome

v0.1.0
------
Initial version.

Requirements:

* Dome
* ts_salobj 5.15
* ts_simactuators 2
* IDL files for MTDomeTrajectory and Dome
