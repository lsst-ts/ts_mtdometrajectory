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

__all__ = ["CONFIG_SCHEMA"]

import yaml

CONFIG_SCHEMA = yaml.safe_load(
    """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_MTDomeTrajectory/blob/master/python/lsst/ts/MTDomeTrajectory/config_schema.py  # noqa
# title must end with one or more spaces followed by the schema version, which must begin with "v"
title: MTDomeTrajectory v1
description: Schema for MTDomeTrajectory configuration files
type: object
properties:
  algorithm_name:
    type: string
    enum:
    - simple
    default: simple
  algorithm_config:
    type: object
allOf:
# For each supported algorithm_name add a new if/then case below.
# Warning: set the default values for each case at the algorithm_config level
# (rather than deeper down on properties within algorithm_config),
# so users can omit algorithm_config and still get proper defaults.
- if:
    properties:
      algorithm_name:
        const: simple
  then:
    properties:
      algorithm_config:
        properties:
          max_delta_azimuth:
            type: number
            description: ->
              Maximum difference between dome and telescope azimuth before moving the dome (deg).
              The default value is nearly where the dome vignettes the telescope.
          max_delta_elevation:
            type: number
            description: ->
              Maximum difference between dome and telescope elevation before moving the dome (deg)
              The default value is nearly where the dome vignettes the telescope.
        required:
        - max_delta_azimuth
        - max_delta_elevation
        default:
          max_delta_azimuth: 5
          max_delta_elevation: 6
        additionalProperties: false
additionalProperties: false
"""
)
