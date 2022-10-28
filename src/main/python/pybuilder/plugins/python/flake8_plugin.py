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

"""
    Plugin for Tarek Ziade"s flake8 script.
    Flake8 is a wrapper around: PyFlakes, pep8, Ned"s McCabe script.

    https://bitbucket.org/tarek/flake8
"""

from pybuilder.core import after, task, init, use_plugin, depends
from pybuilder.errors import BuildFailedException
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder
from pybuilder.utils import tail_log

__author__ = "Michael Gruber"

use_plugin("python.core")


@init
def initialize_flake8_plugin(project):
    project.plugin_depends_on("flake8", "~=4.0")

    project.set_property_if_unset("flake8_break_build", False)
    project.set_property_if_unset("flake8_max_line_length", 120)
    project.set_property_if_unset("flake8_include_patterns", None)
    project.set_property_if_unset("flake8_exclude_patterns", None)
    project.set_property_if_unset("flake8_include_test_sources", False)
    project.set_property_if_unset("flake8_include_scripts", False)
    project.set_property_if_unset("flake8_max_complexity", None)
    project.set_property_if_unset("flake8_ignore", None)
    project.set_property_if_unset("flake8_extend_ignore", None)
    # project.set_property_if_unset("flake8_verbose_output", False)


@after("prepare")
def assert_flake8_is_executable(project, logger, reactor):
    """ Asserts that the flake8 script is executable. """
    logger.debug("Checking if flake8 is executable.")

    reactor.pybuilder_venv.verify_can_execute(command_and_arguments=["flake8", "--version"],
                                              prerequisite="flake8", caller="plugin python.flake8")


@task
@depends("prepare")
def analyze(project, logger, reactor):
    """ Applies the flake8 script to the sources of the given project. """
    logger.info("Executing flake8 on project sources.")

    verbose = project.get_property("verbose")
    project.set_property_if_unset("flake8_verbose_output", verbose)

    command = ExternalCommandBuilder("flake8", project, reactor)
    command.use_argument("--ignore={0}").formatted_with_truthy_property("flake8_ignore")
    command.use_argument("--extend-ignore={0}").formatted_with_truthy_property("flake8_extend_ignore")
    command.use_argument("--max-line-length={0}").formatted_with_property("flake8_max_line_length")
    command.use_argument("--filename={0}").formatted_with_truthy_property("flake8_include_patterns")
    command.use_argument("--exclude={0}").formatted_with_truthy_property("flake8_exclude_patterns")
    command.use_argument("--max-complexity={0}").formatted_with_truthy_property("flake8_max_complexity")

    include_test_sources = project.get_property("flake8_include_test_sources")
    include_scripts = project.get_property("flake8_include_scripts")

    result = command.run_on_production_source_files(logger,
                                                    include_test_sources=include_test_sources,
                                                    include_scripts=include_scripts,
                                                    include_dirs_only=True)

    count_of_warnings = len(result.report_lines)
    count_of_errors = len(result.error_report_lines)

    if count_of_errors > 0:
        logger.error("Errors while running flake8. See %s for full details:\n%s" % (
            result.error_report_file, tail_log(result.error_report_file)))

    if count_of_warnings > 0:
        if project.get_property("flake8_break_build"):
            error_message = "flake8 found {0} warning(s)".format(count_of_warnings)
            raise BuildFailedException(error_message)
        else:
            logger.warn("flake8 found %d warning(s).", count_of_warnings)
