#   Flake8 Plugin for Python-Builder
#
#   Copyright 2012 The Python Builder Team
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

from pythonbuilder.core import after, task, use_plugin
from pythonbuilder.utils import assert_can_execute, read_file
from pythonbuilder.plugins.python.python_plugin_helper import execute_tool_on_source_files


use_plugin("python.core")


@after("prepare")
def assert_flake8_is_executable (logger):
    """
        Asserts that the flake8 script is executable.
    """

    logger.debug("Checking if flake8 is executable.")
    assert_can_execute(command_and_arguments=("flake8",),
                       prerequisite="flake8",
                       caller="plugin python.flake8")


@task
def analyze (project, logger):
    """
        Applies the flake8 script to the sources of the given project.
    """

    logger.info("Applying flake8 to project sources.")
    execution_result  = execute_tool_on_source_files(project=project,
                                                     name="flake8",
                                                     command_and_arguments=["flake8"])
                                           
    report_file       = execution_result[1]
    report_lines      = read_file(report_file)
    count_of_warnings = len(report_lines)

    if count_of_warnings > 0:
        logger.warn("flake8 found %d warning(s).", count_of_warnings)
