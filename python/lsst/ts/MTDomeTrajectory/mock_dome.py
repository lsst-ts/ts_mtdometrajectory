# This file is part of ts_MTDomeTrajectory.
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["MockDome"]

import asyncio

from lsst.ts.idl.enums import MTDome
from lsst.ts import salobj
from lsst.ts import simactuators


class MockDome(salobj.BaseCsc):
    """A very limited fake Dome CSC

    It receives the ``moveAzimuth`` command and outputs:

    * ``azimuthCommandedState`` event
    * ``position`` telemetry.

    It does not enforce motion limits.

    Parameters
    ----------
    initial_state : `salobj.State` or `int` (optional)
        The initial state of the CSC. This is provided for unit testing,
        as real CSCs should start up in `State.STANDBY`, the default.
    initial_elevation : `float`, optional
        Initial elevation.
    azimuth_velocity : `float`, optional
        Maximum azimuth velocity (deg/sec)
    azimuth_acceleration : `float`, optional
        Maximum azimuth acceleration (deg/sec^2)
    elevation_velocity : `float`, optional
        Maximum elevation velocity (deg/sec)
    """

    valid_simulation_modes = [0]

    def __init__(
        self,
        initial_state,
        initial_elevation=0,
        elevation_velocity=3,
        azimuth_velocity=3,
        azimuth_acceleration=1,
    ):
        self.elevation_actuator = simactuators.PointToPointActuator(
            min_position=0,
            max_position=90,
            speed=elevation_velocity,
            start_position=initial_elevation,
        )
        self.azimuth_actuator = simactuators.CircularTrackingActuator(
            max_velocity=azimuth_velocity,
            max_acceleration=azimuth_acceleration,
            dtmax_track=0,
        )
        self.telemetry_interval = 0.2  # seconds
        self.telemetry_loop_task = salobj.make_done_future()
        self.elevation_done_task = salobj.make_done_future()
        self.azimuth_done_task = salobj.make_done_future()

        # Add do methods for unsupported commands
        for name in (
            "crawlAz",
            "crawlEl",
            "park",
            "setLouvers",
            "closeLouvers",
            "stopLouvers",
            "closeShutter",
            "openShutter",
            "stopShutter",
            "setTemperature",
        ):
            setattr(self, f"do_{name}", self._unsupportedCommand)
        super().__init__(name="MTDome", index=None, initial_state=initial_state)

    async def start(self):
        await super().start()
        self.evt_azMotion.set_put(
            state=MTDome.MotionState.STOPPED, inPosition=False,
        )
        self.evt_elMotion.set_put(
            state=MTDome.MotionState.STOPPED, inPosition=False,
        )

    async def close_tasks(self):
        await super().close_tasks()
        self.telemetry_loop_task.cancel()
        self.stop_azimuth()
        self.stop_elevation()

    def get_target_elevation(self):
        """Get the target elevation as an lsst.ts.simactuators.path.PathSegment
        """
        return simactuators.path.PathSegment(
            position=self.elevation_actuator.end_position,
            velocity=0,
            tai=self.elevation_actuator.end_tai,
        )

    def get_target_azimuth(self):
        """Get the target azimuth as an lsst.ts.simactuators.path.PathSegment
        """
        return self.azimuth_actuator.target

    def do_moveEl(self, data):
        self.assert_enabled()
        if not self.elevation_done_task.done():
            raise salobj.ExpectedError("Elevation slew not done.")
        self.elevation_actuator.set_position(position=data.position)
        self.evt_elTarget.set_put(position=data.position, velocity=0, force_output=True)
        self.evt_elMotion.set_put(
            state=MTDome.MotionState.MOVING, inPosition=False,
        )
        self.elevation_done_task = asyncio.create_task(
            self.report_elevation_done(
                in_position=True, motion_state=MTDome.MotionState.STOPPED
            )
        )

    def do_moveAz(self, data):
        self.assert_enabled()
        if not self.azimuth_done_task.done():
            raise salobj.ExpectedError("Azimuth slew not done.")
        self.azimuth_actuator.set_target(
            position=data.position, velocity=data.velocity, tai=salobj.current_tai(),
        )
        self.evt_azTarget.set_put(
            position=data.position, velocity=data.velocity, force_output=True
        )
        self.evt_azMotion.set_put(
            state=MTDome.MotionState.MOVING, inPosition=False,
        )
        end_motion_state = (
            MTDome.MotionState.CRAWLING
            if data.velocity != 0
            else MTDome.MotionState.STOPPED
        )
        self.azimuth_done_task = asyncio.create_task(
            self.report_azimuth_done(in_position=True, motion_state=end_motion_state)
        )

    def do_stopEl(self, data):
        self.assert_enabled()
        self.stop_elevation()

    def do_stopAz(self, data):
        self.assert_enabled()
        self.stop_azimuth()

    def do_stop(self, data):
        self.assert_enabled()
        self.stop_azimuth()
        self.stop_elevation()

    async def handle_summary_state(self):
        if self.disabled_or_enabled:
            if self.telemetry_loop_task.done():
                self.telemetry_loop_task = asyncio.create_task(self.telemetry_loop())
        else:
            self.telemetry_loop_task.cancel()
            self.stop_azimuth()
            self.stop_elevation()

    async def report_azimuth_done(self, in_position, motion_state):
        """Wait for azimuth to stop moving and report evt_azMotion.

        Parameters
        ----------
        in_position : `bool`
            Is the axis in position at the end of the move?
        motion_state : `lsst.ts.idl.MTDome.MotionState`
            Motion state at end of move.
        """
        end_tai = self.azimuth_actuator.path.segments[-1].tai
        duration = end_tai - salobj.current_tai()
        if duration > 0:
            await asyncio.sleep(duration)
        self.evt_azMotion.set_put(
            state=motion_state, inPosition=in_position,
        )

    async def report_elevation_done(self, in_position, motion_state):
        """Wait for elevation to stop moving and report it in position.

        Parameters
        ----------
        in_position : `bool`
            Is the axis in position at the end of the move?
        motion_state : `lsst.ts.idl.MTDome.MotionState`
            Motion state at end of move.
        """
        duration = self.elevation_actuator.remaining_time()
        if duration > 0:
            await asyncio.sleep(duration)
        self.evt_elMotion.set_put(
            state=motion_state, inPosition=in_position,
        )

    def stop_azimuth(self):
        """Stop the azimuth actuator and the done task.

        Report not in position, if changed.

        Unlike do_stopAz this does not require that the CSC is enabled.
        """
        self.azimuth_actuator.stop()
        if self.azimuth_done_task.done():
            return
        self.azimuth_done_task.cancel()
        self.evt_azMotion.set_put(
            state=MTDome.MotionState.STOPPING, inPosition=False,
        )
        self.azimuth_done_task = asyncio.create_task(
            self.report_azimuth_done(
                in_position=False, motion_state=MTDome.MotionState.STOPPED
            )
        )

    def stop_elevation(self):
        """Stop the elevation actuator and the done task.

        Report not in position, if changed.

        Unlike do_stopEl this does not require that the CSC is enabled.
        """
        self.elevation_actuator.stop()
        if self.elevation_done_task.done():
            return
        self.elevation_done_task.cancel()
        self.evt_elMotion.set_put(
            state=MTDome.MotionState.STOPPING, inPosition=False,
        )
        self.evt_elMotion.set_put(
            state=MTDome.MotionState.STOPPED, inPosition=False,
        )

    async def telemetry_loop(self):
        try:
            while True:
                tai = salobj.current_tai()
                azimuth_target = self.azimuth_actuator.target.at(tai)
                azimuth_actual = self.azimuth_actuator.path.at(tai)
                self.tel_azimuth.set_put(
                    positionActual=azimuth_actual.position,
                    positionCommanded=azimuth_target.position,
                    velocityActual=azimuth_actual.velocity,
                    velocityCommanded=azimuth_target.velocity,
                )

                self.tel_lightWindScreen.set_put(
                    positionActual=self.elevation_actuator.position(tai),
                    positionCommanded=self.elevation_actuator.end_position,
                    velocityActual=self.elevation_actuator.velocity(tai),
                    velocityCommanded=0,
                )
                await asyncio.sleep(self.telemetry_interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.log.exception("Telemetry loop failed")
            raise

    def _unsupportedCommand(self, data):
        raise salobj.ExpectedError("Not implemented")
