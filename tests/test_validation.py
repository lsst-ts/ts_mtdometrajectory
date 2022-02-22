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

import jsonschema
import pytest

from lsst.ts import salobj
from lsst.ts import mtdometrajectory


class ValidationTestCase(unittest.TestCase):
    """Test validation of the config schema."""

    def setUp(self):
        self.schema = mtdometrajectory.CONFIG_SCHEMA
        self.validator = salobj.StandardValidator(schema=self.schema)

    def test_basics(self):
        data = dict(
            algorithm_name="simple",
            simple=dict(max_delta_azimuth=3.5, max_delta_elevation=2.2),
        )
        self.validator.validate(data)

    def test_bad_algorithm_name(self):
        data = dict(algorithm_name="invalid_name")
        with pytest.raises(jsonschema.exceptions.ValidationError):
            self.validator.validate(data)

    def test_bad_algorithm_config(self):
        """The current schema only checks for a dict."""
        data = dict(algorithm_name="simple", simple=45)
        with pytest.raises(jsonschema.exceptions.ValidationError):
            self.validator.validate(data)
