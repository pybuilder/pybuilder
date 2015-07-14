#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2015 PyBuilder Team
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

from pybuilder.utils import assert_can_execute
from pybuilder.core import (after,
                            task,
                            init,
                            use_plugin,
                            depends)

__author__ = 'Marcel Wolf'

use_plugin("core")


@init
def initialize_make_deb_plugin(project):

    project.build_depends_on("stdeb")
    project.build_depends_on("subprocess32")


@after("prepare")
def assert_py2dsc_deb_is_available(logger):
    """Asserts that the py2dsc-deb is available.
    """
    logger.debug("Checking if py2dsc-deb is available.")

    assert_can_execute(
        ["py2dsc-deb", "-h"], "py2dsc-deb", "plugin python.py2dsc_deb")


@task("py2dsc_prepare", "prepare for buiding a debian package")
@depends("publish")
def prepare():
    pass


@task("py2dsc_deb", "convert a source tarball into a Debian source package and build a .deb package")
@depends("py2dsc_prepare")
def py2dsc_deb(project, logger):
    """Runs py2dsc-deb against the setup.py for the given project.
    """
    import subprocess32 as subprocess
    logger.info("converting to deb package")
    package_name = project.name + "-" + project.version + ".tar.gz"
    path_to_source_tarball = project.expand_path(
        "$dir_dist/dist/" + package_name)
    path_final_build = project.expand_path("$dir_dist/dist/")

    subprocess.call(["py2dsc-deb", "-d", path_final_build, path_to_source_tarball])
