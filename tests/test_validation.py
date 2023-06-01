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

import pathlib
import unittest

import jsonschema
import pytest
import yaml
from lsst.ts import mtdometrajectory, salobj


class ValidationTestCase(unittest.TestCase):
    """Test validation of the config schema."""

    def setUp(self):
        self.schema = mtdometrajectory.CONFIG_SCHEMA
        self.validator = salobj.StandardValidator(schema=self.schema)
        self.config_dir = pathlib.Path(__file__).parent / "data" / "config"

    def test_basics(self):
        with open(self.config_dir / "_init.yaml", "r") as f:
            data_yaml = f.read()
        data = yaml.safe_load(data_yaml)
        self.validator.validate(data)

    def test_invalid_files(self):
        for path_to_invalid_data in self.config_dir.glob("invalid_*.yaml"):
            with self.subTest(path_to_invalid_data=path_to_invalid_data):
                with open(path_to_invalid_data, "r") as f:
                    invalid_data_yaml = f.read()
                invalid_data = yaml.safe_load(invalid_data_yaml)
                with pytest.raises(jsonschema.exceptions.ValidationError):
                    self.validator.validate(invalid_data)

    def test_missing_field(self):
        with open(self.config_dir / "_init.yaml", "r") as f:
            data_yaml = f.read()
        good_data = yaml.safe_load(data_yaml)
        for missing_field in good_data:
            with self.subTest(missing_field=missing_field):
                bad_data = good_data.copy()
                del bad_data[missing_field]
                with pytest.raises(jsonschema.exceptions.ValidationError):
                    self.validator.validate(bad_data)
