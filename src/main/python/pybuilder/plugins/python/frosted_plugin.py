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
    Frosted is a fork of pyflakes (originally created by Phil Frost) that aims
    at more open contribution from the outside public, a smaller more
    maintainable code base, and a better Python checker for all.

    https://github.com/timothycrosley/frosted
"""

from pybuilder.core import after, task, init, use_plugin, depends
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder

__author__ = 'Maximilien Riehl'


use_plugin("python.core")


@init
def initialize_frosted_plugin(project):
    project.plugin_depends_on("frosted")

    project.set_property("frosted_break_build", False)
    project.set_property("frosted_include_test_sources", False)
    project.set_property("frosted_include_scripts", False)


@after("prepare")
def assert_frosted_is_executable(logger):
    """ Asserts that the frosted script is executable. """
    logger.debug("Checking if frosted is executable.")

    assert_can_execute(command_and_arguments=["frosted", "--version"],
                       prerequisite="frosted (PyPI)",
                       caller="plugin python.frosted")


@task
@depends("prepare")
def analyze(project, logger):
    """ Applies the frosted script to the sources of the given project. """
    logger.info("Executing frosted on project sources.")

    verbose = project.get_property("verbose")
    project.set_property_if_unset("frosted_verbose_output", verbose)

    command = ExternalCommandBuilder('frosted', project)
    for ignored_error_code in project.get_property('frosted_ignore', []):
        command.use_argument('--ignore={0}'.format(ignored_error_code))

    include_test_sources = project.get_property("frosted_include_test_sources")
    include_scripts = project.get_property("frosted_include_scripts")

    result = command.run_on_production_source_files(logger,
                                                    include_test_sources=include_test_sources,
                                                    include_scripts=include_scripts)

    count_of_warnings = len(result.report_lines)
    count_of_errors = len(result.error_report_lines)

    if count_of_errors > 0:
        logger.error('Errors while running frosted, see {0}'.format(result.error_report_file))

    if count_of_warnings > 0:
        if project.get_property("frosted_break_build"):
            error_message = "frosted found {0} warning(s)".format(count_of_warnings)
            raise BuildFailedException(error_message)
        else:
            logger.warn("frosted found %d warning(s).", count_of_warnings)
