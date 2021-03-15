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

import unittest

from lsst.ts.idl.enums import MTDome
from lsst.ts import salobj
from lsst.ts import MTDomeTrajectory

STD_TIMEOUT = 60


class MockDomeTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    def basic_make_csc(self, initial_state, *args, **kwargs):
        """Make and return a CSC.

        initial_state : `lsst.ts.salobj.State` or `int` (optional)
            The initial state of the CSC. Ignored except in simulation mode
            because in normal operation the initial state is the current state
            of the controller.
        """
        return MTDomeTrajectory.MockDome(initial_state=initial_state)

    async def test_initial_output(self):
        async with self.make_csc(initial_state=salobj.State.ENABLED):
            await self.assert_next_summary_state(salobj.State.ENABLED)

            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MTDome.MotionState.STOPPED,
                inPosition=False,
            )
            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MTDome.MotionState.STOPPED,
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
        """Test the moveAz command.
        """
        async with self.make_csc(initial_state=salobj.State.ENABLED):

            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MTDome.MotionState.STOPPED,
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
            tai0 = salobj.current_tai()
            await self.remote.cmd_moveAz.set_start(
                position=position, velocity=velocity, timeout=STD_TIMEOUT
            )
            time_slop = salobj.current_tai() - tai0

            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MTDome.MotionState.MOVING,
                inPosition=False,
            )
            data = await self.assert_next_sample(self.remote.evt_azTarget)
            self.assertAlmostEqual(data.position, position)
            self.assertAlmostEqual(data.velocity, velocity)

            target_azimuth = self.csc.get_target_azimuth()
            self.assertEqual(self.csc.azimuth_actuator.target, target_azimuth)
            self.assertAlmostEqual(target_azimuth.position, position)
            self.assertAlmostEqual(target_azimuth.velocity, velocity)
            self.assertAlmostEqual(target_azimuth.tai, tai0, delta=time_slop)

            self.assertAlmostEqual(self.csc.azimuth_actuator.target.position, position)
            self.assertAlmostEqual(self.csc.azimuth_actuator.target.velocity, velocity)
            self.assertAlmostEqual(
                self.csc.azimuth_actuator.target.tai, tai0, delta=time_slop
            )

            end_segment = self.csc.azimuth_actuator.path.segments[-1]
            desired_end_position = position + velocity * (end_segment.tai - tai0)
            position_slop = velocity * time_slop
            self.assertAlmostEqual(
                end_segment.position, desired_end_position, delta=position_slop
            )
            self.assertAlmostEqual(end_segment.velocity, velocity)
            duration = end_segment.tai - tai0
            print(f"duration={duration:0.2f} seconds")
            self.assertGreater(duration, 1)

            # Check that a new move before the slew is done is rejected
            # (though we hope the dome controller will eventually allow this).
            with salobj.assertRaisesAckError():
                await self.remote.cmd_moveAz.set_start(
                    position=position, velocity=velocity, timeout=STD_TIMEOUT
                )

            # Wait for the move to finish.
            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MTDome.MotionState.CRAWLING,
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
                state=MTDome.MotionState.MOVING,
                inPosition=False,
            )
            data = await self.assert_next_sample(self.remote.evt_azTarget, velocity=0)
            self.assertAlmostEqual(data.position, position2)
            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MTDome.MotionState.STOPPED,
                inPosition=True,
            )

    async def test_move_el(self):
        """Test the moveEl and stopEl commands.
        """
        async with self.make_csc(initial_state=salobj.State.ENABLED):

            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MTDome.MotionState.STOPPED,
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
                state=MTDome.MotionState.MOVING,
                inPosition=False,
            )
            data = await self.assert_next_sample(self.remote.evt_elTarget, velocity=0)
            self.assertAlmostEqual(data.position, position)

            target_elevation = self.csc.get_target_elevation()
            self.assertAlmostEqual(target_elevation.position, position)
            duration = self.csc.elevation_actuator.remaining_time()
            print(f"duration={duration:0.2f} seconds")
            self.assertGreater(duration, 1)

            # Check that a new move before the slew is done is rejected
            # (though we hope the vendor will change to allow this).
            with salobj.assertRaisesAckError():
                await self.remote.cmd_moveEl.set_start(
                    position=position, timeout=STD_TIMEOUT
                )

            # Wait for the move to finish.
            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MTDome.MotionState.STOPPED,
                inPosition=True,
            )

            # Check that a new move after the slew is done is accepted.
            position2 = 5
            await self.remote.cmd_moveEl.set_start(
                position=position2, timeout=STD_TIMEOUT
            )
            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MTDome.MotionState.MOVING,
                inPosition=False,
            )
            data = await self.assert_next_sample(self.remote.evt_elTarget, velocity=0)
            self.assertAlmostEqual(data.position, position2)
            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MTDome.MotionState.STOPPED,
                inPosition=True,
            )

    async def test_stop_az(self):
        """Test the stopAz command.
        """
        async with self.make_csc(initial_state=salobj.State.ENABLED):

            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MTDome.MotionState.STOPPED,
                inPosition=False,
            )

            position = 20
            velocity = -1
            await self.remote.cmd_moveAz.set_start(
                position=position, velocity=velocity, timeout=STD_TIMEOUT
            )

            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MTDome.MotionState.MOVING,
                inPosition=False,
            )
            data = await self.assert_next_sample(self.remote.evt_azTarget)
            self.assertAlmostEqual(data.position, position)
            self.assertAlmostEqual(data.velocity, velocity)

            await self.remote.cmd_stopAz.start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MTDome.MotionState.STOPPING,
                inPosition=False,
            )
            await self.assert_next_sample(
                self.remote.evt_azMotion,
                state=MTDome.MotionState.STOPPED,
                inPosition=False,
            )

    async def test_stop_el(self):
        """Test the stopEl command.
        """
        async with self.make_csc(initial_state=salobj.State.ENABLED):

            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MTDome.MotionState.STOPPED,
                inPosition=False,
            )

            position = 30
            await self.remote.cmd_moveEl.set_start(
                position=position, timeout=STD_TIMEOUT
            )

            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MTDome.MotionState.MOVING,
                inPosition=False,
            )
            data = await self.assert_next_sample(self.remote.evt_elTarget, velocity=0)
            self.assertAlmostEqual(data.position, position)

            await self.remote.cmd_stopEl.start(timeout=STD_TIMEOUT)
            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MTDome.MotionState.STOPPING,
                inPosition=False,
            )
            await self.assert_next_sample(
                self.remote.evt_elMotion,
                state=MTDome.MotionState.STOPPED,
                inPosition=False,
            )


if __name__ == "__main__":
    unittest.main()
