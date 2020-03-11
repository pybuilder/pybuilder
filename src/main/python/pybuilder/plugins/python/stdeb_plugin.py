#   -*- coding: utf-8 -*-
#
#   This file is part of PyBuilder
#
#   Copyright 2011-2020 PyBuilder Team
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

from pybuilder.core import NAME_ATTRIBUTE
from pybuilder.core import (after,
                            task,
                            init,
                            use_plugin,
                            depends)
from pybuilder.errors import BuildFailedException
from pybuilder.utils import (tail_log
                             )

__author__ = 'Marcel Wolf'

DEB_PACKAGE_MAINTAINER = "John Doe <changeme@example.com>"

use_plugin("core")


@init
def initialize_make_deb_plugin(project):
    project.plugin_depends_on("stdeb")

    package_name = project.name + "-" + project.version + ".tar.gz"

    PATH_TO_SOURCE_TARBALL = project.expand_path("$dir_dist", "dist", package_name)
    PATH_FINAL_BUILD = project.expand_path("$dir_dist", "dist")

    project.set_property_if_unset(
        "deb_package_maintainer", DEB_PACKAGE_MAINTAINER)
    project.set_property_if_unset(
        "path_final_build", PATH_FINAL_BUILD)
    project.set_property_if_unset(
        "path_to_source_tarball", PATH_TO_SOURCE_TARBALL)


@after("prepare")
def assert_py2dsc_deb_is_available(project, logger, reactor):
    """Asserts that the py2dsc-deb is available.
    """
    logger.debug("Checking if py2dsc-deb is available.")

    reactor.pybuilder_venv.verify_can_execute(["py2dsc-deb", "-h"], "py2dsc-deb",
                                              "plugin python.stdeb")


@after("prepare")
def assert_dpkg_is_available(project, logger, reactor):
    """Asserts that the dpkg-buildpackage is available.
    """
    logger.debug("Checking if dpkg-buildpackage is available")

    reactor.pybuilder_venv.verify_can_execute(["dpkg-buildpackage", "--help"], "dpkg-buildpackage",
                                              "plugin python.stdeb")


@task("make_deb", "converts a source tarball into a Debian source package and build a .deb package")
@depends("publish")
def py2dsc_deb(project, logger, reactor):
    """Runs py2dsc-deb against the setup.py for the given project.
    """
    task_name = getattr(py2dsc_deb, NAME_ATTRIBUTE)
    build_command = get_py2dsc_deb_command(project)
    run_py2dsc_deb_build(reactor.pybuilder_venv, build_command, task_name, logger, project)


def get_py2dsc_deb_command(project):
    """Builds the py2dsc_deb command using project properties.
        py2dsc_deb parameters:
        :param --maintainer: maintainer name and email to use.
        :param -d: directory to put final built.
    """

    return ["py2dsc-deb", "--maintainer", project.get_property("deb_package_maintainer"),
            "-d", project.get_property("path_final_build"),
            project.get_property("path_to_source_tarball")]


def run_py2dsc_deb_build(python_env, build_command, task_name, logger, project):
    logger.info("Running %s" % task_name)
    log_file = project.expand_path("$dir_target", "reports", task_name)
    if project.get_property("verbose"):
        logger.info(build_command)
        exit_code = python_env.execute_command(build_command, log_file, shell=True)
        if exit_code != 0:
            raise BuildFailedException(
                "py2dsc_deb build command failed. See %s for full details:\n%s", log_file, tail_log(log_file))
