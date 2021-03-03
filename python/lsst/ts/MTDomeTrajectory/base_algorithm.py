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

__all__ = ["AlgorithmRegistry", "BaseAlgorithm"]

import abc


AlgorithmRegistry = dict()


class BaseAlgorithm(abc.ABC):
    """Abstract class to handle different dome trajectory algorithms.

    Parameters
    ----------
    **kwargs : `dict` of `str`: `value`
        Configuration. For details see the ``configure`` method
        for the algorithm in question.
    """

    def __init__(self, **kwargs):
        self.configure(**kwargs)

    @abc.abstractmethod
    def desired_dome_elevation(
        self, dome_target_elevation, telescope_target, next_telescope_target=None
    ):
        """Compute the desired dome elevation.

        Parameters
        ----------
        dome_target_elevation : `lsst.ts.simactuators.path.PathSegment` \
        or `None`
            Dome target elevation, or `None` if unknown.
        telescope_target : `ElevationAzimuth`
            Telescope target elevation and azimuth.
        next_telescope_target : `ElevationAzimuth` or `None`, optional
            Next telescope_target target elevation and azimuth, if known,
            else `None`.

        Returns
        -------
        dome_target_elevation : `lsst.ts.simactuators.path.PathSegment` \
        or `None`
            New desired dome elevation, or `None` if no change.
        """
        pass

    @abc.abstractmethod
    def desired_dome_azimuth(
        self, dome_target_azimuth, telescope_target, next_telescope_target=None
    ):
        """Compute the desired dome azimuth.

        Parameters
        ----------
        dome_target_azimuth : `lsst.ts.simactuators.path.PathSegment` or `None`
            Dome target azimuth, or `None` if unknown.
        telescope_target : `ElevationAzimuth`
            Telescope target elevation and azimuth.
        next_telescope_target : `ElevationAzimuth` or `None`, optional
            Next telescope_target target elevation and azimuth, if known,
            else `None`.

        Returns
        -------
        dome_target_azimuth : `lsst.ts.simactuators.path.PathSegment` or `None`
            New desired dome azimuth, or `None` if no change.
        """
        pass

    @abc.abstractmethod
    def configure(self, **kwargs):
        """Configure the algorithm.
        """
        pass
