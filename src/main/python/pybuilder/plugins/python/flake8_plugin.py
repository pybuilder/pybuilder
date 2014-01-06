#   Flake8 Plugin for PyBuilder
#
#   Copyright 2011-2014 PyBuilder Team
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
    Plugin for Tarek Ziade's flake8 script.
    Flake8 is a wrapper around: PyFlakes, pep8, Ned's McCabe script.

    https://bitbucket.org/tarek/flake8
"""

__author__ = 'Michael Gruber'

from pybuilder.core import after, task, init, use_plugin, depends
from pybuilder.errors import BuildFailedException
from pybuilder.utils import assert_can_execute, read_file
from pybuilder.plugins.python.python_plugin_helper import execute_tool_on_source_files


use_plugin("python.core")


@init
def initialize_flake8_plugin(project):
    project.build_depends_on("flake8")
    project.set_property("flake8_break_build", False)
    project.set_property("flake8_max_line_length", 120)
    project.set_property("flake8_exclude_patterns", None)
    project.set_property("flake8_include_test_sources", False)


@after("prepare")
def assert_flake8_is_executable(logger):
    """ Asserts that the flake8 script is executable. """
    logger.debug("Checking if flake8 is executable.")

    assert_can_execute(command_and_arguments=["flake8", "--version"],
                       prerequisite="flake8",
                       caller="plugin python.flake8")


@task
@depends("prepare")
def analyze(project, logger):
    """ Applies the flake8 script to the sources of the given project. """
    logger.info("Executing flake8 on project sources.")

    verbose = project.get_property("verbose")
    project.set_property_if_unset("flake8_verbose_output", verbose)

    command_and_arguments = ["flake8"]

    flake8_ignore = project.get_property("flake8_ignore")
    if flake8_ignore is not None:
        ignore_option = "--ignore={0}".format(flake8_ignore)
        command_and_arguments.append(ignore_option)

    max_line_length = project.get_property("flake8_max_line_length")
    command_and_arguments.append("--max-line-length={0}".format(max_line_length))

    exclude_patterns = project.get_property("flake8_exclude_patterns")
    if exclude_patterns:
        command_and_arguments.append("--exclude={0}".format(exclude_patterns))

    include_test_sources = project.get_property("flake8_include_test_sources")

    execution_result = execute_tool_on_source_files(project=project,
                                                    name="flake8",
                                                    command_and_arguments=command_and_arguments,
                                                    logger=logger,
                                                    include_test_sources=include_test_sources)

    report_file = execution_result[1]
    report_lines = read_file(report_file)
    count_of_warnings = len(report_lines)

    if count_of_warnings > 0:
        if project.get_property("flake8_break_build"):
            error_message = "flake8 found {0} warning(s)".format(count_of_warnings)
            raise BuildFailedException(error_message)
        else:
            logger.warn("flake8 found %d warning(s).", count_of_warnings)
