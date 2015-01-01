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

"""Plugin for Sphinx.
"""

__author__ = 'Thomas Prebble'

from pybuilder.core import after
from pybuilder.core import depends
from pybuilder.core import init
from pybuilder.core import task
from pybuilder.core import use_plugin
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute
from pybuilder.utils import execute_command


use_plugin("core")


DEFAULT_SPHINX_BUILDER = "html"
DEFAULT_SPHINX_SOURCE_DIR = ""
DEFAULT_SPHINX_OUTPUT_DIR = "_build/"


@init
def initialize_sphinx_plugin(project):
    project.build_depends_on("sphinx")
    project.set_property_if_unset("sphinx_builder", DEFAULT_SPHINX_BUILDER)
    project.set_property_if_unset("sphinx_config_path", DEFAULT_SPHINX_SOURCE_DIR)
    project.set_property_if_unset("sphinx_source_dir", DEFAULT_SPHINX_SOURCE_DIR)
    project.set_property_if_unset("sphinx_output_dir", DEFAULT_SPHINX_OUTPUT_DIR)


@after("prepare")
def assert_sphinx_is_available(logger):
    """Asserts that the sphinx-build script is available.
    """
    logger.debug("Checking if sphinx-build is available.")

    assert_can_execute(["sphinx-build", "--version"], "sphinx", "plugin python.sphinx")


@task("sphinx_generate_documentation", "Generates documentation with sphinx")
@depends("prepare")
def sphinx_generate(project, logger):
    """Runs sphinx-build against rst sources for the given project.
    """
    logger.info("Running sphinx-build")

    log_file = project.expand_path("$dir_target/reports/{0}".format("sphinx-build"))
    build_command = get_sphinx_build_command(project)

    if project.get_property("verbose"):
        logger.info(build_command)

    exit_code = execute_command(build_command, log_file, shell=True)
    if exit_code != 0:
        raise BuildFailedException("Sphinx build command failed. See %s for details.", log_file)


def get_sphinx_build_command(project):
    """Builds the sphinx-build command using project properties.
    """
    options = ["-b %s" % project.get_property("sphinx_builder"),
               "-c %s" % project.expand_path(project.get_property("sphinx_config_path")),
               project.expand_path(project.get_property("sphinx_source_dir")),
               project.expand_path(project.get_property("sphinx_output_dir"))]
    return "sphinx-build %s" % " ".join(options)
