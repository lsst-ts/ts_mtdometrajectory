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

__all__ = ["CONFIG_SCHEMA"]

import yaml

CONFIG_SCHEMA = yaml.safe_load(
    """
$schema: http://json-schema.org/draft-07/schema#
$id: https://github.com/lsst-ts/ts_mtdometrajectory/blob/master/python/lsst/ts/mtdometrajectory/config_schema.py  # noqa
# title must end with one or more spaces followed by the schema version, which must begin with "v"
title: MTDomeTrajectory v4
description: Schema for MTDomeTrajectory configuration files
type: object
properties:
  algorithm_name:
    type: string
    enum:
      - simple
  simple:
    description: Configuration for the "simple" algorithm.
    type: object
    properties:
      max_delta_azimuth:
        type: number
        description: ->
          Maximum difference between dome and telescope azimuth before moving the dome (deg).
          The desired value is nearly where the dome vignettes the telescope.
      max_delta_elevation:
        type: number
        description: ->
          Maximum difference between dome and telescope elevation before moving the dome (deg)
          The desired value is nearly where the dome vignettes the telescope.
    required:
      - max_delta_azimuth
      - max_delta_elevation
    additionalProperties: false
  azimuth_vignette_partial:
    description: >-
      Azimuth angle difference (deg) above which the telescope is partially vignetted
      when the telescope is at elevation 0 (horizon). This is approximately 2.7°.
    type: number
  azimuth_vignette_full:
    description: >-
      Azimuth angle difference (deg) above which the telescope is fully vignetted
      when the telescope is at elevation 0 (horizon). This is approximately 35°
    type: number
  elevation_vignette_partial:
    description: >-
      Elevation angle difference (deg) above which the telescope is partially vignetted.
      This is approximately 1.3°.
    type: number
  elevation_vignette_full:
    description: >-
      Elevation angle difference (deg) above which the telescope is fully vignetted
      This is approximately 44°.
    type: number
  shutter_vignette_partial:
    description: >-
      Shutter open percentage (%) below which the telescope is partially vignetted.
    type: number
  shutter_vignette_full:
    description: >-
      Shutter open percentage (%) below which the telescope is fully vignetted.
      This probably needs to be a bit larger than 0, to take into account noise in the reported value
      and/or essentially no light getting through in the last bit of travel.
    type: number
  enable_el_motion:
    description: >-
      Enable elevation motion or not.
      This should be set to False at least for the summit until the dome light and wind screen is supported.
      For BTS and TTS this can be set to True.
    type: boolean
required:
  - algorithm_name
  - simple
  - azimuth_vignette_partial
  - azimuth_vignette_full
  - elevation_vignette_partial
  - elevation_vignette_full
  - shutter_vignette_partial
  - shutter_vignette_full
  - enable_el_motion
additionalProperties: false
"""
)
