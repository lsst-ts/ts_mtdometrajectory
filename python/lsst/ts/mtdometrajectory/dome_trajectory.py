# This file is part of ts_mtdometrajectory.
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

__all__ = ["MTDomeTrajectory", "run_mtdometrajectory"]

import asyncio
import math

import yaml
from lsst.ts import salobj, simactuators, utils
from lsst.ts.xml.enums.MTDomeTrajectory import TelescopeVignetted

from . import __version__
from .base_algorithm import AlgorithmRegistry
from .config_schema import CONFIG_SCHEMA
from .elevation_azimuth import ElevationAzimuth

# Timeout for commands [s].
STD_TIMEOUT = 120

# Time (sec) between polling for vignetting.
VIGNETTING_MONITOR_INTERVAL = 0.1


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
    override : `str`, optional
        Configuration override file to apply if ``initial_state`` is
        `State.DISABLED` or `State.ENABLED`.
    """

    valid_simulation_modes = [0]
    version = __version__

    def __init__(
        self,
        config_dir=None,
        initial_state=salobj.State.STANDBY,
        override="",
    ):
        super().__init__(
            name="MTDomeTrajectory",
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            index=None,
            initial_state=initial_state,
            override=override,
            simulation_mode=0,
        )

        # Telescope target, from the MTMount target event;
        # an ElevationAzimuth; None before a target is seen.
        self.telescope_target = None

        # Next telescope target, eventually from the scheduler;
        # an ElevationAzimuth; None before the next target is seen;
        self.next_telescope_target = None

        self.enable_el_motion = False

        # Tasks that start dome azimuth and elevation motion
        # and wait for the motionState and target events
        # that indicate the motion has started.
        # While one of these is running that axis will not be commanded.
        # This avoids the problem of new telescope target events
        # causing unwanted motion when the dome has been commanded
        # but has not yet had a chance to report the fact.
        self.move_dome_azimuth_task = utils.make_done_future()
        self.move_dome_elevation_task = utils.make_done_future()

        # Task that is set to (moved_elevation, moved_azimuth)
        # whenever the follow_target method runs.
        self.follow_task = asyncio.Future()

        self.mtmount_remote = salobj.Remote(
            domain=self.domain,
            name="MTMount",
            include=["azimuth", "elevation", "summaryState", "target"],
        )
        self.dome_remote = salobj.Remote(
            domain=self.domain,
            name="MTDome",
            include=[
                "apertureShutter",
                "azimuth",
                "lightWindScreen",
                "azMotion",
                "azTarget",
                "elMotion",
                "elTarget",
                "summaryState",
            ],
        )

        self.mtmount_remote.evt_target.callback = self.update_mtmount_target
        self.report_vignetted_task = utils.make_done_future()

        self.algorithm = None
        self.config = None

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
            await self.evt_followingMode.set_write(enabled=True)
            await self.follow_target()
        else:
            await self.evt_followingMode.set_write(enabled=False)
            self.move_dome_azimuth_task.cancel()
            self.move_dome_elevation_task.cancel()

    def compute_vignetted_by_any(self, *, azimuth, elevation, shutter):
        """Compute the ``vignetted`` field of the telescopeVignetted event."""
        if (
            azimuth == TelescopeVignetted.UNKNOWN
            # or elevation == TelescopeVignetted.UNKNOWN
            or shutter == TelescopeVignetted.UNKNOWN
        ):
            return TelescopeVignetted.UNKNOWN
        elif (
            azimuth == TelescopeVignetted.NO
            # and elevation == TelescopeVignetted.NO
            and shutter == TelescopeVignetted.NO
        ):
            return TelescopeVignetted.NO
        elif (
            azimuth == TelescopeVignetted.FULLY
            # or elevation == TelescopeVignetted.FULLY
            or shutter == TelescopeVignetted.FULLY
        ):
            return TelescopeVignetted.FULLY
        return TelescopeVignetted.PARTIALLY

    def compute_vignetted_by_azimuth(
        self, dome_azimuth, telescope_azimuth, telescope_elevation
    ):
        """Compute the ``azimuth`` field of the telescopeVignetted event.

        Parameters
        ----------
        dome_azimuth : `float` | None
            Dome current azimuth (deg); None if unknown.
        telescope_azimuth : `float` | None
            Telescope current azimuth (deg); None if unknown.
        telescope_elevation : `float` | None
            Telescope current elevation (deg); None if unknown.

        Returns
        -------
        azimuth : `TelescopeVignetted`
            Telescope vignetted by azimuth mismatch between telescope and dome.
        """
        if (
            dome_azimuth is None
            or telescope_azimuth is None
            or telescope_elevation is None
        ):
            return TelescopeVignetted.UNKNOWN

        abs_azimuth_difference = abs(
            utils.angle_diff(dome_azimuth, telescope_azimuth).deg
        )
        scaled_abs_azimuth_difference = abs_azimuth_difference * math.cos(
            math.radians(telescope_elevation)
        )
        if scaled_abs_azimuth_difference < self.config.azimuth_vignette_partial:
            return TelescopeVignetted.NO
        elif scaled_abs_azimuth_difference < self.config.azimuth_vignette_full:
            return TelescopeVignetted.PARTIALLY
        return TelescopeVignetted.FULLY

    def compute_vignetted_by_elevation(self, dome_elevation, telescope_elevation):
        """Compute the ``elevation`` field of the telescopeVignetted event.

        Parameters
        ----------
        dome_elevation : `float` | None
            Dome current elevation (deg); None if unknown.
        telescope_elevation : `float` | None
            Telescope current elevation (deg); None if unknown.

        Returns
        -------
        elevation : `TelescopeVignetted`
            Telescope vignetted by elevation mismatch between telescope
            and dome.
        """
        if dome_elevation is None or telescope_elevation is None:
            return TelescopeVignetted.UNKNOWN
        if self.enable_el_motion:
            abs_elevation_difference = abs(
                utils.angle_diff(dome_elevation, telescope_elevation).deg
            )
            if abs_elevation_difference < self.config.elevation_vignette_partial:
                return TelescopeVignetted.NO
            elif abs_elevation_difference < self.config.elevation_vignette_full:
                return TelescopeVignetted.PARTIALLY
            return TelescopeVignetted.FULLY
        else:
            return TelescopeVignetted.NO

    def compute_vignetted_by_shutter(self, shutters_percent_open):
        """Compute the ``shutter`` field of the telescopeVignetted event.

        Parameters
        ----------
        shutters_percent_open : [`float`, `float`] | None
            Current open percentage (%) of both dome shutters; None if unknown.

        Returns
        -------
        shutter : `TelescopeVignetted`
            Telescope vignetted by dome shutter.
        """

        if shutters_percent_open is None:
            return TelescopeVignetted.UNKNOWN
        if (
            shutters_percent_open[0] >= self.config.shutter_vignette_partial
            and shutters_percent_open[1] >= self.config.shutter_vignette_partial
        ):
            return TelescopeVignetted.NO
        elif (
            shutters_percent_open[0] <= self.config.shutter_vignette_full
            and shutters_percent_open[1] <= self.config.shutter_vignette_full
        ):
            return TelescopeVignetted.FULLY
        return TelescopeVignetted.PARTIALLY

    async def configure(self, config):
        """Configure this CSC and output the ``algorithm`` event.

        Parameters
        ----------
        config : `types.SimpleNamespace`
            Configuration, as described by `CONFIG_SCHEMA`
        """
        algorithm_name = config.algorithm_name
        if algorithm_name not in AlgorithmRegistry:
            raise salobj.ExpectedError(f"Unknown algorithm {algorithm_name}.")
        algorithm_config = getattr(config, config.algorithm_name)
        self.algorithm = AlgorithmRegistry[config.algorithm_name](**algorithm_config)
        self.config = config
        self.enable_el_motion = config.enable_el_motion
        await self.evt_algorithm.set_write(
            algorithmName=config.algorithm_name,
            algorithmConfig=yaml.dump(algorithm_config),
        )

    async def close_tasks(self):
        self.move_dome_azimuth_task.cancel()
        self.move_dome_elevation_task.cancel()
        self.report_vignetted_task.cancel()
        await self.evt_telescopeVignetted.set_write(
            vignetted=TelescopeVignetted.UNKNOWN,
            azimuth=TelescopeVignetted.UNKNOWN,
            shutter=TelescopeVignetted.UNKNOWN,
        )
        await super().close_tasks()

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
            tai=utils.current_tai(),
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
            tai=utils.current_tai(),
        )

    def get_dome_azimuth(self):
        """Get current actual dome azimuth (deg), or None if unavailable."""
        azimuth_data = self.dome_remote.tel_azimuth.get()
        return None if azimuth_data is None else azimuth_data.positionActual

    def get_dome_elevation(self):
        """Get current actual dome elevation (deg), or None if unavailable."""
        elevation_data = self.dome_remote.tel_lightWindScreen.get()
        return None if elevation_data is None else elevation_data.positionActual

    def get_shutters_percent_open(self):
        """Get the current open percentage of both shutters, or None
        if unavailable.
        """
        shutter_data = self.dome_remote.tel_apertureShutter.get()
        return None if shutter_data is None else shutter_data.positionActual

    def get_dome_summary_state(self):
        """Get MTDome summary state, or None if unavailable."""
        dome_state = self.dome_remote.evt_summaryState.get()
        return None if dome_state is None else dome_state.summaryState

    def get_telescope_azimuth(self):
        """Get current telescope azimuth (deg), or None if unavailable."""
        azimuth_data = self.mtmount_remote.tel_azimuth.get()
        return None if azimuth_data is None else azimuth_data.actualPosition

    def get_telescope_elevation(self):
        """Get current telescope elevation (deg), or None if unavailable."""
        elevation_data = self.mtmount_remote.tel_elevation.get()
        return None if elevation_data is None else elevation_data.actualPosition

    def get_telescope_summary_state(self):
        """Get MTMount summary state, or None if unavailable."""
        telescope_state = self.mtmount_remote.evt_summaryState.get()
        return None if telescope_state is None else telescope_state.summaryState

    async def handle_summary_state(self):
        if self.summary_state != salobj.State.ENABLED:
            self.move_dome_azimuth_task.cancel()
            self.move_dome_elevation_task.cancel()
            self.report_vignetted_task.cancel()
            await self.evt_followingMode.set_write(enabled=False)
        if self.disabled_or_enabled:
            if self.report_vignetted_task.done():
                self.report_vignetted_task = asyncio.create_task(
                    self.report_vignetted_loop()
                )
        else:
            self.report_vignetted_task.cancel()
            await self.evt_telescopeVignetted.set_write(
                vignetted=TelescopeVignetted.UNKNOWN,
                azimuth=TelescopeVignetted.UNKNOWN,
                shutter=TelescopeVignetted.UNKNOWN,
            )

    async def report_vignetted_loop(self):
        """Poll MTDome & MTMount topics to report telescopeVignetted event."""
        self.log.info("report_vignetted_loop begins.")
        ok_states = frozenset((salobj.State.DISABLED, salobj.State.ENABLED))
        try:
            while True:
                dome_state = self.get_dome_summary_state()
                telescope_state = self.get_telescope_summary_state()
                if dome_state not in ok_states or telescope_state not in ok_states:
                    azimuth = TelescopeVignetted.UNKNOWN
                    elevation = TelescopeVignetted.UNKNOWN
                    shutter = TelescopeVignetted.UNKNOWN
                else:
                    telescope_azimuth = self.get_telescope_azimuth()
                    telescope_elevation = self.get_telescope_elevation()
                    dome_azimuth = self.get_dome_azimuth()
                    dome_elevation = self.get_dome_elevation()
                    shutters_percent_open = self.get_shutters_percent_open()
                    azimuth = self.compute_vignetted_by_azimuth(
                        dome_azimuth=dome_azimuth,
                        telescope_azimuth=telescope_azimuth,
                        telescope_elevation=telescope_elevation,
                    )
                    elevation = self.compute_vignetted_by_elevation(
                        dome_elevation=dome_elevation,
                        telescope_elevation=telescope_elevation,
                    )
                    shutter = self.compute_vignetted_by_shutter(
                        shutters_percent_open=shutters_percent_open
                    )

                vignetted = self.compute_vignetted_by_any(
                    azimuth=azimuth, elevation=elevation, shutter=shutter
                )
                await self.evt_telescopeVignetted.set_write(
                    vignetted=vignetted,
                    azimuth=azimuth,
                    elevation=elevation,
                    shutter=shutter,
                )
                await asyncio.sleep(VIGNETTING_MONITOR_INTERVAL)
        except asyncio.CancelledError:
            self.log.info("report_vignetted_loop ends.")
        except Exception:
            self.log.exception("report_vignetted_loop failed.")
        await self.evt_telescopeVignetted.set_write(
            vignetted=TelescopeVignetted.UNKNOWN,
            azimuth=TelescopeVignetted.UNKNOWN,
            shutter=TelescopeVignetted.UNKNOWN,
        )

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
            # Make sure that the target angle is in the range [0, 360).
            azimuth=simactuators.path.PathSegment(
                position=utils.angle_wrap_nonnegative(target.azimuth).deg,
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
            and self.enable_el_motion
        ):
            moved_elevation = self.get_moved_elevation()

        if (
            self.move_dome_azimuth_task.done()
            and self.dome_remote.evt_azMotion.has_data
        ):
            moved_azimuth = self.get_moved_azimuth()
        else:
            self.log.debug("Previous dome azimuth motion still not finished.")

        if not self.follow_task.done():
            self.follow_task.set_result((moved_elevation, moved_azimuth))

    def get_moved_elevation(self):
        moved_elevation = False
        dome_target_elevation = self.get_dome_target_elevation()
        desired_dome_elevation = self.algorithm.desired_dome_elevation(
            dome_target_elevation=dome_target_elevation,
            telescope_target=self.telescope_target,
            next_telescope_target=self.next_telescope_target,
        )
        if desired_dome_elevation is not None and math.isfinite(
            desired_dome_elevation.position
        ):
            moved_elevation = True
            self.move_dome_elevation_task = asyncio.create_task(
                self.move_dome_elevation(desired_dome_elevation)
            )
        else:
            self.log.warning(
                f"{desired_dome_elevation=} too small or invalid; not moving the dome elevation."
            )
        return moved_elevation

    def get_moved_azimuth(self):
        moved_azimuth = False
        dome_target_azimuth = self.get_dome_target_azimuth()
        desired_dome_azimuth = self.algorithm.desired_dome_azimuth(
            dome_target_azimuth=dome_target_azimuth,
            telescope_target=self.telescope_target,
            next_telescope_target=self.next_telescope_target,
        )
        if (
            desired_dome_azimuth is not None
            and math.isfinite(desired_dome_azimuth.position)
            and math.isfinite(desired_dome_azimuth.velocity)
        ):
            moved_azimuth = True
            self.move_dome_azimuth_task = asyncio.create_task(
                self.move_dome_azimuth(desired_dome_azimuth)
            )
        else:
            self.log.warning(
                f"{desired_dome_azimuth=} too small or invalid; not moving the dome azimuth."
            )
        return moved_azimuth

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
                self.log.warning(
                    "No data for Dome elMotion event; not moving the dome elevation."
                )
                return

            # Move the dome elevation axis and wait for the target event
            # and the first motion event (so motion has started).
            self.dome_remote.evt_elTarget.flush()
            self.log.debug(
                f"Start dome elevation motion with {desired_dome_elevation.position=}."
            )
            await self.dome_remote.cmd_moveEl.set_start(
                position=desired_dome_elevation.position,
                timeout=STD_TIMEOUT,
            )
            await self.dome_remote.evt_elTarget.next(flush=False, timeout=STD_TIMEOUT)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.log.exception("Failed to move dome in elevation.")
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
                    "No data for the Dome azMotion event; not moving the dome azimuth."
                )
                return

            # Move the dome azimuth axis and wait for the target event
            # and the first motion event (so motion has started).
            self.dome_remote.evt_azTarget.flush()
            self.log.debug(
                "Start dome azimuth motion with "
                f"{desired_dome_azimuth.position=} and {desired_dome_azimuth.velocity=}."
            )
            await self.dome_remote.cmd_moveAz.set_start(
                position=desired_dome_azimuth.position,
                velocity=desired_dome_azimuth.velocity,
                timeout=STD_TIMEOUT,
            )
            await self.dome_remote.evt_azTarget.next(flush=False, timeout=STD_TIMEOUT)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.log.exception("Failed to move dome in azimuth.")
            raise

    async def start(self):
        await super().start()
        await self.dome_remote.start_task


def run_mtdometrajectory():
    asyncio.run(MTDomeTrajectory.amain(index=None))
