# This file is part of ts_MTDomeTrajectory.
#
# Developed for Vera C. Rubin Observatory Telescope and Site Systems.
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

__all__ = ["MTDomeTrajectory"]

import asyncio
import math

import yaml

from lsst.ts.idl.enums import MTDome
from lsst.ts import salobj
from lsst.ts import simactuators
from . import __version__
from .config_schema import CONFIG_SCHEMA
from .elevation_azimuth import ElevationAzimuth
from .base_algorithm import AlgorithmRegistry

# Timeout for commands that should be executed quickly
STD_TIMEOUT = 5


class MTDomeTrajectory(salobj.ConfigurableCsc):
    """MTDomeTrajectory CSC

    MTDomeTrajectory commands the dome to follow the telescope,
    using an algorithm you specify in the configuration file.
    It supports no commands beyond the standard commands.

    Parameters
    ----------
    config_dir : `str` (optional)
        Directory of configuration files, or None for the standard
        configuration directory (obtained from `get_default_config_dir`).
        This is provided for unit testing.
    initial_state : `salobj.State` (optional)
        The initial state of the CSC. Typically one of:
        - State.ENABLED if you want the CSC immediately usable.
        - State.STANDBY if you want full emulation of a CSC.
    settings_to_apply : `str`, optional
        Settings to apply if ``initial_state`` is `State.DISABLED`
        or `State.ENABLED`.
    """

    valid_simulation_modes = [0]
    version = __version__

    def __init__(
        self,
        config_dir=None,
        initial_state=salobj.base_csc.State.STANDBY,
        settings_to_apply="",
    ):
        super().__init__(
            name="MTDomeTrajectory",
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            index=None,
            initial_state=initial_state,
            settings_to_apply=settings_to_apply,
            simulation_mode=0,
        )

        # Telescope target, from the MTMount target event;
        # an ElevationAzimuth; None before a target is seen.
        self.telescope_target = None

        # Next telescope target, eventually from the scheduler;
        # an ElevationAzimuth; None before the next target is seen;
        self.next_telescope_target = None

        # Tasks that start dome azimuth and elevation motion
        # and wait for the motionState and target events
        # that indicate the motion has started.
        # While one of these is running that axis will not be commanded.
        # This avoids the problem of new telescope target events
        # causing unwanted motion when the dome has been commanded
        # but has not yet had a chance to report the fact.
        self.move_dome_azimuth_task = salobj.make_done_future()
        self.move_dome_elevation_task = salobj.make_done_future()

        # Task that is set to (moved_elevation, moved_azimuth)
        # whenever the follow_target method runs.
        self.follow_task = asyncio.Future()

        self.mtmount_remote = salobj.Remote(
            domain=self.domain, name="MTMount", include=["target"]
        )
        self.dome_remote = salobj.Remote(
            domain=self.domain,
            name="MTDome",
            include=["azMotion", "azTarget", "elMotion", "elTarget"],
        )

        self.mtmount_remote.evt_target.callback = self.update_mtmount_target

    @staticmethod
    def get_config_pkg():
        return "ts_config_mttcs"

    @property
    def following_enabled(self):
        """Is following enabled?

        False if the CSC is not in the ENABLED state
        or if following is not enabled.
        """
        if self.summary_state != salobj.State.ENABLED:
            return False
        return self.evt_followingMode.data.enabled

    async def do_setFollowingMode(self, data):
        """Handle the setFollowingMode command."""
        self.assert_enabled()
        if data.enable:
            # Report following enabled and trigger an update
            self.evt_followingMode.set_put(enabled=True)
            await self.follow_target()
        else:
            self.evt_followingMode.set_put(enabled=False)
            self.move_dome_azimuth_task.cancel()

    def get_dome_target_elevation(self):
        """Get the current dome elevation target."""
        target = self.dome_remote.evt_elTarget.get()
        if target is None:
            return None
        if math.isnan(target.position):
            return None
        return simactuators.path.PathSegment(
            position=target.position,
            velocity=target.velocity,
            tai=salobj.current_tai(),
        )

    def get_dome_target_azimuth(self):
        """Get the current dome azimuth target."""
        target = self.dome_remote.evt_azTarget.get()
        if target is None:
            return None
        if math.isnan(target.position):
            return None
        return simactuators.path.PathSegment(
            position=target.position,
            velocity=target.velocity,
            tai=salobj.current_tai(),
        )

    async def configure(self, config):
        """Configure this CSC and output the ``algorithm`` event.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by `CONFIG_SCHEMA`
        """
        algorithm_name = config.algorithm_name
        if algorithm_name not in AlgorithmRegistry:
            raise salobj.ExpectedError(f"Unknown algorithm {algorithm_name}")
        algorithm_config = getattr(config, config.algorithm_name)
        self.algorithm = AlgorithmRegistry[config.algorithm_name](**algorithm_config)
        self.evt_algorithm.set_put(
            algorithmName=config.algorithm_name,
            algorithmConfig=yaml.dump(algorithm_config),
        )

    async def handle_summary_state(self):
        if not self.summary_state == salobj.State.ENABLED:
            self.move_dome_azimuth_task.cancel()
            self.move_dome_elevation_task.cancel()
            self.evt_followingMode.set_put(enabled=False)

    async def update_mtmount_target(self, target):
        """Callback for MTMount target event.

        This is triggered in any summary state, but only
        commands a new dome position if enabled.
        """
        telescope_target = ElevationAzimuth(
            elevation=simactuators.path.PathSegment(
                position=target.elevation,
                velocity=target.elevationVelocity,
                tai=target.taiTime,
            ),
            azimuth=simactuators.path.PathSegment(
                position=target.azimuth,
                velocity=target.azimuthVelocity,
                tai=target.taiTime,
            ),
        )
        self.telescope_target = telescope_target
        await self.follow_target()

    async def follow_target(self):
        """Send the dome to a new position, if appropriate.

        This has no effect unless the summary state is ENABLED,
        the CSC and remotes have fully started,
        and the target azimuth is known.
        """
        if not self.following_enabled:
            return
        if not self.start_task.done():
            return
        if self.telescope_target is None:
            return
        moved_elevation = False
        moved_azimuth = False

        if (
            self.move_dome_elevation_task.done()
            and self.dome_remote.evt_elMotion.has_data
        ):
            dome_target_elevation = self.get_dome_target_elevation()
            desired_dome_elevation = self.algorithm.desired_dome_elevation(
                dome_target_elevation=dome_target_elevation,
                telescope_target=self.telescope_target,
                next_telescope_target=self.next_telescope_target,
            )
            if desired_dome_elevation is not None:
                moved_elevation = True
                self.move_dome_elevation_task = asyncio.create_task(
                    self.move_dome_elevation(desired_dome_elevation)
                )

        if (
            self.move_dome_azimuth_task.done()
            and self.dome_remote.evt_azMotion.has_data
        ):
            dome_target_azimuth = self.get_dome_target_azimuth()
            desired_dome_azimuth = self.algorithm.desired_dome_azimuth(
                dome_target_azimuth=dome_target_azimuth,
                telescope_target=self.telescope_target,
                next_telescope_target=self.next_telescope_target,
            )
            if desired_dome_azimuth is not None:
                moved_azimuth = True
                self.move_dome_azimuth_task = asyncio.create_task(
                    self.move_dome_azimuth(desired_dome_azimuth)
                )

        if not self.follow_task.done():
            self.follow_task.set_result((moved_elevation, moved_azimuth))

    def make_follow_task(self):
        """Make and return a task that is set when the follow method runs.

        The result of the task is (moved_elevation, moved_azimuth).
        This method is intended for unit tests.
        """
        self.follow_task = asyncio.Future()
        return self.follow_task

    async def move_dome_elevation(self, desired_dome_elevation):
        """Start moving the dome elevation axis.

        Wait until the dome has reported that it is moving,
        via the elMotion and elTarget events.

        This will log a warning and return if evt_elMotion has no data.

        Parameters
        ----------
        desired_dome_elevation : `lsst.ts.simactuators.path.PathSegment`
            Desired dome elevation. The velocity is ignored.
        """
        try:
            dome_el_motion_state = self.dome_remote.evt_elMotion.get()
            if dome_el_motion_state is None:
                self.log.warning("No data for Dome elMotion event; not moving the dome")
                return

            # Stop the dome elevation axis, if moving, and wait for it to stop,
            # since the dome does not allow one move to supersede another.
            if dome_el_motion_state.state == MTDome.MotionState.MOVING:
                self.log.info("Stop existing dome elevation motion")
                self.dome_remote.evt_elMotion.flush()
                await self.dome_remote.cmd_stopEl.start(timeout=STD_TIMEOUT)

                while dome_el_motion_state.state != MTDome.MotionState.STOPPED:
                    dome_el_motion_state = await self.dome_remote.evt_elMotion.next(
                        flush=False
                    )

            # Move the dome elevation axis and wait for the target event
            # and the first motion event (so motion has started).
            self.dome_remote.evt_elTarget.flush()
            self.log.debug("Start dome elevation motion")
            await self.dome_remote.cmd_moveEl.set_start(
                position=desired_dome_elevation.position,
                timeout=STD_TIMEOUT,
            )
            await self.dome_remote.evt_elTarget.next(flush=False, timeout=STD_TIMEOUT)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.log.exception("move_dome_elevation failed")
            raise

    async def move_dome_azimuth(self, desired_dome_azimuth):
        """Start moving the dome azimuth axis.

        Wait until the dome has reported that it is moving,
        via the azMotion and azTarget events.

        This will log a warning and return if evt_azMotion has no data.

        Parameters
        ----------
        desired_dome_azimuth : `lsst.ts.simactuators.path.PathSegment`
            Desired dome azimuth.
        """
        try:
            dome_az_motion_state = self.dome_remote.evt_azMotion.get()
            if dome_az_motion_state is None:
                self.log.warning(
                    "No data for the Dome azMotion event; not moving the dome"
                )
                return

            # Stop the dome azimuth axis, if moving, and wait for it to stop,
            # since the dome does not allow one move to supersede another.
            if dome_az_motion_state.state == MTDome.MotionState.MOVING:
                self.dome_remote.evt_azMotion.flush()
                self.log.info("Stop existing dome azimuth motion")
                await self.dome_remote.cmd_stopAz.start(timeout=STD_TIMEOUT)

                while dome_az_motion_state.state != MTDome.MotionState.STOPPED:
                    dome_az_motion_state = await self.dome_remote.evt_azMotion.next(
                        flush=False
                    )

            # Move the dome azimuth axis and wait for the target event
            # and the first motion event (so motion has started).
            self.dome_remote.evt_azTarget.flush()
            self.log.debug("Start dome azimuth motion")
            await self.dome_remote.cmd_moveAz.set_start(
                position=desired_dome_azimuth.position,
                velocity=desired_dome_azimuth.velocity,
                timeout=STD_TIMEOUT,
            )
            await self.dome_remote.evt_azTarget.next(flush=False, timeout=STD_TIMEOUT)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.log.exception("move_dome_azimuth failed")
            raise

    async def start(self):
        await super().start()
        await self.dome_remote.start_task
