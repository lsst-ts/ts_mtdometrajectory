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

import unittest

import pytest
from lsst.ts import mtdometrajectory, salobj, utils
from lsst.ts.xml.enums.MTDome import MotionState

STD_TIMEOUT = 60


class MockDomeTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    def basic_make_csc(self, initial_state, *args, **kwargs):
        """Make and return a CSC.

        initial_state : `lsst.ts.salobj.State` or `int` (optional)
            The initial state of the CSC. Ignored except in simulation mode
            because in normal operation the initial state is the current state
            of the controller.
        """
        return mtdometrajectory.MockDome(initial_state=initial_state)

    async def test_initial_output(self):
        async with self.make_csc(initial_state=salobj.State.ENABLED):
            await self.assert_next_summary_state(salobj.State.ENABLED)

            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MotionState.STOPPED,
                inPosition=False,
            )
            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MotionState.STOPPED,
                inPosition=False,
            )

            await self.assert_next_sample(
                self.remote.tel_lightWindScreen,
                flush=True,
                positionActual=0,
                positionCommanded=0,
            )
            await self.assert_next_sample(
                self.remote.tel_azimuth,
                flush=True,
                positionActual=0,
                positionCommanded=0,
            )

    async def test_move_az(self):
        """Test the moveAz command."""
        async with self.make_csc(initial_state=salobj.State.ENABLED):
            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MotionState.STOPPED,
                inPosition=False,
            )

            await self.assert_next_sample(
                self.remote.tel_azimuth,
                flush=True,
                positionActual=0,
                positionCommanded=0,
            )

            position = 2
            velocity = 0.1
            tai0 = utils.current_tai()
            await self.remote.cmd_moveAz.set_start(
                position=position, velocity=velocity, timeout=STD_TIMEOUT
            )
            time_slop = utils.current_tai() - tai0

            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MotionState.MOVING,
                inPosition=False,
            )
            data = await self.assert_next_sample(self.remote.evt_azTarget)
            assert data.position == pytest.approx(position)
            assert data.velocity == pytest.approx(velocity)

            target_azimuth = self.csc.get_target_azimuth()
            assert self.csc.azimuth_actuator.target == target_azimuth
            assert target_azimuth.position == pytest.approx(position)
            assert target_azimuth.velocity == pytest.approx(velocity)
            assert target_azimuth.tai == pytest.approx(tai0, abs=time_slop)

            assert self.csc.azimuth_actuator.target.position == pytest.approx(position)
            assert self.csc.azimuth_actuator.target.velocity == pytest.approx(velocity)
            assert self.csc.azimuth_actuator.target.tai == pytest.approx(
                tai0, abs=time_slop
            )

            end_segment = self.csc.azimuth_actuator.path.segments[-1]
            desired_end_position = position + velocity * (end_segment.tai - tai0)
            position_slop = velocity * time_slop
            assert end_segment.position == pytest.approx(
                desired_end_position, abs=position_slop
            )
            assert end_segment.velocity == pytest.approx(velocity)
            duration = end_segment.tai - tai0
            print(f"duration={duration:0.2f} seconds")
            assert duration > 0.5

            # Wait for the move to finish.
            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MotionState.CRAWLING,
                inPosition=True,
            )

            # Check that a new move after the slew is done is accepted,
            # and that a move to zero velocity is reported as STOPPED.
            position2 = 2.5
            await self.remote.cmd_moveAz.set_start(
                position=position2, velocity=0, timeout=STD_TIMEOUT
            )
            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MotionState.MOVING,
                inPosition=False,
            )
            data = await self.assert_next_sample(self.remote.evt_azTarget, velocity=0)
            assert data.position == pytest.approx(position2)
            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MotionState.STOPPED,
                inPosition=True,
            )

    async def test_move_el(self):
        """Test the moveEl and stopEl commands."""
        async with self.make_csc(initial_state=salobj.State.ENABLED):
            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MotionState.STOPPED,
                inPosition=False,
            )

            await self.assert_next_sample(
                self.remote.tel_lightWindScreen,
                flush=True,
                positionActual=0,
                positionCommanded=0,
            )

            position = 6
            await self.remote.cmd_moveEl.set_start(
                position=position, timeout=STD_TIMEOUT
            )

            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MotionState.MOVING,
                inPosition=False,
            )
            data = await self.assert_next_sample(self.remote.evt_elTarget, velocity=0)
            assert data.position == pytest.approx(position)

            target_elevation = self.csc.get_target_elevation()
            assert target_elevation.position == pytest.approx(position)
            duration = self.csc.elevation_actuator.remaining_time()
            print(f"duration={duration:0.2f} seconds")
            assert duration > 0.2

            # Wait for the move to finish.
            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MotionState.STOPPED,
                inPosition=True,
            )

            # Check that a new move after the slew is done is accepted.
            position2 = 5
            await self.remote.cmd_moveEl.set_start(
                position=position2, timeout=STD_TIMEOUT
            )
            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MotionState.MOVING,
                inPosition=False,
            )
            data = await self.assert_next_sample(self.remote.evt_elTarget, velocity=0)
            assert data.position == pytest.approx(position2)
            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MotionState.STOPPED,
                inPosition=True,
            )
