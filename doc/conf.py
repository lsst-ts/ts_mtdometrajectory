"""Sphinx configuration file for an LSST stack package.

This configuration only affects single-package Sphinx documentation builds.
"""

from documenteer.conf.pipelinespkg import *  # type: ignore # noqa
import lsst.ts.mtdometrajectory  # noqa

project = "ts_mtdometrajectory"
html_theme_options["logotext"] = project  # type: ignore # noqa
html_title = project
html_short_title = project
# Avoid warning: Could not find tag file _doxygen/doxygen.tag
doxylink = {}  # type: ignore

intersphinx_mapping["ts_xml"] = ("https://ts-xml.lsst.io", None)  # type: ignore # noqa
intersphinx_mapping["ts_salobj"] = ("https://ts-salobj.lsst.io", None)  # type: ignore # noqa
