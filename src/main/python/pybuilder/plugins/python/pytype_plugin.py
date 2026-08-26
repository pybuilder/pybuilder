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

"""
    Plugin for Google's pytype tester.
"""

from pybuilder.core import task, init, use_plugin, after, depends
from pybuilder.errors import BuildFailedException
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder
from pybuilder.utils import assert_can_execute

use_plugin("python.core")


@init
def initialize_pytype_plugin(project):
    """ Init default plugin project properties. """
    project.plugin_depends_on('pytype')
    project.set_property_if_unset("pytype_break_build", False)


@after("prepare")
def assert_pytype_is_executable(logger):
    """ Asserts that the pytype script is executable. """
    logger.debug("Checking if pytype is executable.")
    assert_can_execute(command_and_arguments=["pytype", "--version"],
                       prerequisite="pytype",
                       caller="plugin pyb_pytype")


@task
@depends("prepare")
def analyze(project, logger):
    """ Call pytype for the sources of the given project. """
    logger.info("Executing pytype on project sources.")
    verbose = project.get_property("verbose")

    command = ExternalCommandBuilder('pytype', project)
    if verbose:
        command.use_argument('--verbosity=2')

    result = command.run_on_production_source_files(logger,
                                                    include_test_sources=True,
                                                    include_scripts=True,
                                                    include_dirs_only=True)
    count_of_errors = len(result.error_report_lines)

    if count_of_errors > 0:
        if project.get_property("pytype_break_build"):
            error_message = "pytype found {0} warning(s)".format(
                count_of_errors)
            raise BuildFailedException(error_message)
        else:
            logger.warn("pytype found %d warning(s).", count_of_errors)
