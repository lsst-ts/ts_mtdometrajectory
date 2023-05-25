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

import asyncio
import contextlib
import logging
import math
import os
import pathlib
import unittest

import pytest
import yaml
from lsst.ts import mtdometrajectory, salobj, utils
from lsst.ts.idl.enums.MTDome import MotionState

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

STD_TIMEOUT = 30  # standard command timeout (sec)
TEST_CONFIG_DIR = pathlib.Path(__file__).parents[1].joinpath("tests", "data", "config")
NODATA_TIMEOUT = 0.5  # Timeout when no data expected (sec)

RAD_PER_DEG = math.pi / 180


class MTDomeTrajectoryTestCase(
    salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase
):
    @contextlib.asynccontextmanager
    async def make_csc(
        self,
        initial_state,
        config_dir=None,
        initial_elevation=0,
        override="",
        simulation_mode=0,
        log_level=None,
    ):
        async with super().make_csc(
            initial_state=initial_state,
            config_dir=config_dir,
            override=override,
            simulation_mode=simulation_mode,
            log_level=log_level,
        ), mtdometrajectory.MockDome(
            initial_state=salobj.State.ENABLED, initial_elevation=initial_elevation
        ) as self.dome_csc, salobj.Remote(
            domain=self.dome_csc.domain, name="MTDome"
        ) as self.dome_remote, salobj.Controller(
            "MTMount"
        ) as self.mtmount_controller:
            yield

    def basic_make_csc(
        self,
        initial_state,
        config_dir,
        simulation_mode,
        override="",
    ):
        assert simulation_mode == 0
        return mtdometrajectory.MTDomeTrajectory(
            initial_state=initial_state,
            config_dir=config_dir,
            override=override,
        )

    async def test_bin_script(self):
        """Test that run_mtdometrajectory runs the CSC."""
        await self.check_bin_script(
            name="MTDomeTrajectory",
            index=None,
            exe_name="run_mtdometrajectory",
        )

    async def test_standard_state_transitions(self):
        """Test standard CSC state transitions."""
        async with self.make_csc(initial_state=salobj.State.STANDBY):
            await self.assert_next_sample(
                topic=self.remote.evt_softwareVersions,
                cscVersion=mtdometrajectory.__version__,
                subsystemVersions="",
            )

            await self.check_standard_state_transitions(
                enabled_commands=("setFollowingMode",)
            )

    async def test_simple_follow(self):
        """Test that dome follows telescope using the "simple" algorithm."""
        initial_elevation = 40
        async with self.make_csc(
            initial_state=salobj.State.ENABLED, initial_elevation=initial_elevation
        ):
            await self.assert_next_sample(self.remote.evt_followingMode, enabled=False)
            await self.assert_next_sample(
                self.dome_remote.evt_azMotion, state=MotionState.STOPPED
            )
            await self.assert_next_sample(
                self.dome_remote.evt_elMotion, state=MotionState.STOPPED
            )

            await self.remote.cmd_setFollowingMode.set_start(
                enable=True, timeout=STD_TIMEOUT
            )
            await self.assert_next_sample(self.remote.evt_followingMode, enabled=True)
            assert self.csc.following_enabled

            min_del_to_move = self.csc.algorithm.max_delta_elevation
            initial_azimuth = 0
            for elevation, azimuth, move_elevation, move_azimuth, wait_dome_done in (
                (initial_elevation, initial_azimuth, True, True, True),
                (
                    initial_elevation,
                    initial_azimuth
                    + self.scaled_max_delta_azimuth(initial_elevation)
                    + 0.001,
                    False,
                    True,
                    True,
                ),
                (
                    initial_elevation + min_del_to_move + 0.001,
                    initial_azimuth,
                    True,
                    False,
                    True,
                ),
                (85, 180, True, True, False),
                (initial_elevation, initial_azimuth, True, True, True),
            ):
                await self.check_move(
                    elevation=elevation,
                    azimuth=azimuth,
                    move_elevation=move_elevation,
                    move_azimuth=move_azimuth,
                    wait_dome_done=wait_dome_done,
                )

            await self.check_null_moves()

            # Turn off following and make sure the dome does not follow
            # the telescope.
            await self.remote.cmd_setFollowingMode.set_start(
                enable=False, timeout=STD_TIMEOUT
            )
            await self.assert_next_sample(self.remote.evt_followingMode, enabled=False)
            # Pretend the telescope is pointing 180 deg away from the dome;
            # that is more than enough to trigger a dome move, if following.
            new_telescope_azimuth = self.dome_csc.get_target_azimuth().position + 180
            await self.mtmount_controller.evt_target.set_write(
                elevation=elevation, azimuth=new_telescope_azimuth, force_output=True
            )
            await self.assert_dome_azimuth(
                expected_azimuth=None,
                move_expected=False,
            )

    async def test_default_config_dir(self):
        async with self.make_csc(initial_state=salobj.State.STANDBY):
            desired_config_pkg_name = "ts_config_mttcs"
            desired_config_env_name = desired_config_pkg_name.upper() + "_DIR"
            desird_config_pkg_dir = os.environ[desired_config_env_name]
            desired_config_dir = (
                pathlib.Path(desird_config_pkg_dir) / "MTDomeTrajectory/v3"
            )
            assert self.csc.get_config_pkg() == desired_config_pkg_name
            assert self.csc.config_dir == desired_config_dir
            await self.csc.do_exitControl(data=None)
            await asyncio.wait_for(self.csc.done_task, timeout=5)

    async def test_configuration(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=TEST_CONFIG_DIR
        ):
            assert self.csc.summary_state == salobj.State.STANDBY
            await self.assert_next_summary_state(salobj.State.STANDBY)

            for bad_config_name in (
                "no_such_file.yaml",
                "invalid_no_such_algorithm.yaml",
                "invalid_malformed.yaml",
                "invalid_bad_max_daz.yaml",
            ):
                with self.subTest(bad_config_name=bad_config_name):
                    self.remote.cmd_start.set(configurationOverride=bad_config_name)
                    with salobj.assertRaisesAckError():
                        await self.remote.cmd_start.start(timeout=STD_TIMEOUT)

            self.remote.cmd_start.set(configurationOverride="valid.yaml")
            await self.remote.cmd_start.start(timeout=STD_TIMEOUT)
            assert self.csc.summary_state == salobj.State.DISABLED
            await self.assert_next_summary_state(salobj.State.DISABLED)
            settings = await self.remote.evt_algorithm.next(
                flush=False, timeout=STD_TIMEOUT
            )
            assert settings.algorithmName == "simple"
            # max_delta_elevation and max_delta_azimuth are hard coded
            # in data/config/valid.yaml
            assert yaml.safe_load(settings.algorithmConfig) == dict(
                max_delta_azimuth=7.1, max_delta_elevation=5.5
            )

    async def assert_dome_azimuth(self, expected_azimuth, move_expected):
        """Check the Dome and MTDomeController commanded azimuth.

        Parameters
        ----------
        expected_azimuth : `float`
            Expected new azimuth position (deg);
            ignored if ``move_expected`` false.
        move_expected : `bool`
            Is a move expected?

        Notes
        -----
        If ``move_expected`` then read the next ``azTarget`` MTDome event.
        Otherwise try to read the next event and expect it to time out.
        """
        if move_expected:
            dome_azimuth_target = await self.dome_remote.evt_azTarget.next(
                flush=False, timeout=STD_TIMEOUT
            )
            utils.assert_angles_almost_equal(
                dome_azimuth_target.position, expected_azimuth
            )
        else:
            with pytest.raises(asyncio.TimeoutError):
                await self.dome_remote.evt_azTarget.next(
                    flush=False, timeout=NODATA_TIMEOUT
                )

    async def assert_dome_elevation(self, expected_elevation, move_expected):
        """Check the Dome and MTDomeController commanded elevation.

        Parameters
        ----------
        expected_elevation : `float`
            Expected new elevation position (deg);
            ignored if ``move_expected`` false.
        move_expected : `bool`
            Is a move expected?

        Notes
        -----
        If ``move_expected`` then read one ``elTarget`` Dome event.
        """
        if move_expected:
            dome_elevation_target = await self.dome_remote.evt_elTarget.next(
                flush=False, timeout=STD_TIMEOUT
            )
            utils.assert_angles_almost_equal(
                dome_elevation_target.position, expected_elevation
            )
        else:
            with pytest.raises(asyncio.TimeoutError):
                await self.dome_remote.evt_elTarget.next(
                    flush=False, timeout=NODATA_TIMEOUT
                )

    def assert_telescope_target(self, expected_elevation, expected_azimuth):
        utils.assert_angles_almost_equal(
            self.csc.telescope_target.elevation.position, expected_elevation
        )
        utils.assert_angles_almost_equal(
            self.csc.telescope_target.azimuth.position, expected_azimuth
        )

    def scaled_max_delta_azimuth(self, elevation):
        """max_delta_azimuth scaled by cos(elevation).

        Thus the minimum azimuth difference that will trigger a dome move
        for the simple algorithm.
        """
        return self.csc.algorithm.max_delta_azimuth / math.cos(elevation * RAD_PER_DEG)

    async def check_move(
        self, elevation, azimuth, move_elevation, move_azimuth, wait_dome_done
    ):
        """Set telescope target azimuth and elevation.

        Check that the dome moves there in azimuth or elevation,
        as requested.
        Then check that the dome does not move for small changes
        to the telescope target about that point.

        Parameters
        ----------
        elevation : `float`
            Desired elevation for telescope (deg)
        azimuth : `float`
            Desired azimuth for telescope and dome (deg)
        move_elevation : `bool`
            Move the dome in elevation?
        move_azimuth : 'bool`
            Move the dome in azimuth?
        wait_dome_done : `bool`
            Wait for the dome move to finish?

        Raises
        ------
        ValueError :
            If the change in dome azimuth <= configured max dome azimuth error
            (since that will result in no dome motion, which will mess up
            the test).
        """
        print(
            f"check_move: elevation={elevation}, azimuth={azimuth}; "
            f"move_elevation={move_elevation}, move_azimuth={move_azimuth}; "
            f"wait_dome_done={wait_dome_done}"
        )
        assert move_azimuth or move_elevation

        # Wait until the dome is ready to receive a new MTMount target.
        await asyncio.wait_for(
            asyncio.gather(
                self.csc.move_dome_elevation_task, self.csc.move_dome_azimuth_task
            ),
            timeout=STD_TIMEOUT,
        )

        # Is the dome moving?
        elevation_was_moving = self.dome_is_moving(self.dome_remote.evt_elMotion)
        azimuth_was_moving = self.dome_is_moving(self.dome_remote.evt_azMotion)

        # Set telescope target
        follow_task = self.csc.make_follow_task()
        await self.mtmount_controller.evt_target.set_write(
            elevation=elevation, azimuth=azimuth, force_output=True
        )

        follow_result = await asyncio.wait_for(follow_task, timeout=STD_TIMEOUT)
        assert follow_result == (move_elevation, move_azimuth)

        # Check that the dome starts moving as expected.
        def expected_states(was_moving):
            if was_moving:
                return [
                    MotionState.STOPPING,
                    MotionState.STOPPED,
                    MotionState.MOVING,
                ]
            return [MotionState.MOVING]

        if move_azimuth:
            for azimuth_state in expected_states(was_moving=azimuth_was_moving):
                await self.assert_next_sample(
                    self.dome_remote.evt_azMotion, state=azimuth_state
                )
        if move_elevation:
            for elevation_state in expected_states(was_moving=elevation_was_moving):
                await self.assert_next_sample(
                    self.dome_remote.evt_elMotion, state=elevation_state
                )
        await self.assert_dome_elevation(
            expected_elevation=elevation, move_expected=move_elevation
        )
        await self.assert_dome_azimuth(
            expected_azimuth=azimuth, move_expected=move_azimuth
        )

        # Make sure the dome does not move for small changes in telescope
        # target around the current dome target.
        # This is only safe if we have waited for the dome to stop moving
        # as the test relies on dome motion events timing out.
        if wait_dome_done:
            if move_azimuth:
                await self.assert_next_sample(
                    self.dome_remote.evt_azMotion, inPosition=True, timeout=STD_TIMEOUT
                )
            if move_elevation:
                await self.assert_next_sample(
                    self.dome_remote.evt_elMotion, inPosition=True, timeout=STD_TIMEOUT
                )
            if move_azimuth and move_elevation:
                await self.check_null_moves()

    def dome_is_moving(self, event):
        """Return True if the dome axis is MOVING, false if STOPPED
        or the event has never been set.

        Raise an exception for any other value.
        """
        data = event.get()
        if data is None:
            return False
        if data.state == MotionState.MOVING:
            return True
        if data.state == MotionState.STOPPED:
            return False
        self.fail(f"Unexpected {event} state {data.state}")

    async def check_null_moves(self):
        """Check that small telescope moves do not trigger dome motion.

        Prerequisite: the telescope and dome target positions must match.
        Thus the dome must have just moved in both elevation and azimuth.
        """
        dome_target_azimuth = self.dome_csc.get_target_azimuth()
        dome_target_elevation = self.dome_csc.get_target_elevation()
        no_move_delta_elevation = self.csc.algorithm.max_delta_elevation - 0.001
        min_elevation = dome_target_elevation.position - no_move_delta_elevation
        max_elevation = dome_target_elevation.position + no_move_delta_elevation
        for target_elevation, target_azimuth in (
            (
                min_elevation,
                dome_target_azimuth.position
                - self.scaled_max_delta_azimuth(min_elevation)
                + 0.001,
            ),
            (
                max_elevation,
                dome_target_azimuth.position
                + self.scaled_max_delta_azimuth(max_elevation)
                - 0.001,
            ),
            (dome_target_elevation.position, dome_target_azimuth.position),
        ):
            follow_task = self.csc.make_follow_task()
            await self.mtmount_controller.evt_target.set_write(
                elevation=target_elevation, azimuth=target_azimuth, force_output=True
            )
            follow_result = await asyncio.wait_for(follow_task, timeout=STD_TIMEOUT)
            assert follow_result == (False, False)
